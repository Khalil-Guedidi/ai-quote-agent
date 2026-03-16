#!/usr/bin/env python3
"""Seed Odoo with a synthetic dirty product catalog (~500+ products).

Connects to Odoo via JSON-RPC and creates industrial products with realistic
noise: duplicates, case variations, missing fields, HTML descriptions,
abbreviations, archived/non-sellable items.

Reads connection settings from prototype/.env or environment variables.
"""

import json
import os
import random
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration (from .env or environment)
# ---------------------------------------------------------------------------

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path) -> None:
    """Minimal .env loader — no external dependency."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


load_env(ENV_PATH)

ODOO_HOST = os.environ.get("ODOO_HOST", "localhost")
ODOO_PORT = os.environ.get("ODOO_PORT", "8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo_db")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

BASE_URL = f"http://{ODOO_HOST}:{ODOO_PORT}"

# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------


class OdooRPC:
    """Thin wrapper around Odoo JSON-RPC."""

    def __init__(self, base_url: str, db: str, login: str, password: str):
        self.base_url = base_url
        self.db = db
        self.password = password
        self.session = requests.Session()
        self.uid = self._authenticate(login, password)

    def _authenticate(self, login: str, password: str) -> int:
        resp = self.session.post(
            f"{self.base_url}/web/session/authenticate",
            json={
                "jsonrpc": "2.0",
                "params": {"db": self.db, "login": login, "password": password},
            },
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        uid = result.get("uid")
        if not uid:
            raise RuntimeError(f"Authentication failed: {resp.json()}")
        return uid

    def execute_kw(self, model: str, method: str, args: list, kwargs: dict | None = None):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [self.db, self.uid, self.password, model, method, args, kwargs or {}],
            },
        }
        resp = self.session.post(f"{self.base_url}/jsonrpc", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Odoo RPC error: {json.dumps(data['error'], indent=2)}")
        return data.get("result")

    def search_count(self, model: str, domain: list | None = None) -> int:
        return self.execute_kw(model, "search_count", [domain or []])

    def create(self, model: str, values_list: list[dict]) -> list[int]:
        return self.execute_kw(model, "create", [values_list])


# ---------------------------------------------------------------------------
# Product categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Acier & Métaux",
    "Boulonnerie & Fixations",
    "Tuyauterie & Raccords",
    "Composants Électriques",
    "Équipements de Sécurité",
    "Outillage Industriel",
    "Joints & Étanchéité",
    "Peinture & Traitement de Surface",
]

# ---------------------------------------------------------------------------
# Product templates — each category has base products that get variations
# ---------------------------------------------------------------------------

PRODUCT_TEMPLATES = {
    "Acier & Métaux": [
        {"base": "Tôle acier laminée à chaud", "code_prefix": "TOL", "price_range": (25, 500)},
        {"base": "Tôle inox 304L", "code_prefix": "TINX", "price_range": (80, 800)},
        {"base": "Plaque acier S235", "code_prefix": "PLA", "price_range": (50, 600)},
        {"base": "Rond plein acier", "code_prefix": "RPA", "price_range": (10, 150)},
        {"base": "Tube carré acier", "code_prefix": "TCA", "price_range": (15, 200)},
        {"base": "Fer plat", "code_prefix": "FPL", "price_range": (8, 90)},
        {"base": "Cornière acier", "code_prefix": "COR", "price_range": (12, 120)},
        {"base": "Profilé IPE", "code_prefix": "IPE", "price_range": (40, 350)},
        {"base": "Profilé HEA", "code_prefix": "HEA", "price_range": (50, 400)},
        {"base": "Poutre UPN", "code_prefix": "UPN", "price_range": (30, 280)},
        {"base": "Barre filetée acier zingué", "code_prefix": "BFZ", "price_range": (5, 45)},
        {"base": "Tôle aluminium", "code_prefix": "TAL", "price_range": (30, 350)},
    ],
    "Boulonnerie & Fixations": [
        {"base": "Boulon tête hexagonale", "abbrev": "Boul. HM", "code_prefix": "BHM", "price_range": (0.5, 15)},
        {"base": "Écrou hexagonal", "abbrev": "Écr. HM", "code_prefix": "EHM", "price_range": (0.2, 8)},
        {"base": "Rondelle plate", "abbrev": "Rond. PL", "code_prefix": "RPL", "price_range": (0.1, 5)},
        {"base": "Vis à tête cylindrique", "abbrev": "Vis CHC", "code_prefix": "VCHC", "price_range": (0.3, 12)},
        {"base": "Tige filetée", "abbrev": "Tige fil.", "code_prefix": "TF", "price_range": (2, 25)},
        {"base": "Goujon d'ancrage", "abbrev": "Gouj. anc.", "code_prefix": "GA", "price_range": (3, 30)},
        {"base": "Cheville métallique", "abbrev": "Chev. mét.", "code_prefix": "CHM", "price_range": (1, 15)},
        {"base": "Rivet aveugle", "abbrev": "Riv. av.", "code_prefix": "RIV", "price_range": (0.1, 5)},
    ],
    "Tuyauterie & Raccords": [
        {"base": "Tuyau acier", "code_prefix": "TUY", "price_range": (10, 200)},
        {"base": "Coude acier 90°", "code_prefix": "COU", "price_range": (5, 80)},
        {"base": "Bride plate", "code_prefix": "BRP", "price_range": (8, 120)},
        {"base": "Réduction concentrique", "code_prefix": "RED", "price_range": (6, 90)},
        {"base": "Vanne à boisseau sphérique", "abbrev": "Vanne BS", "code_prefix": "VBS", "price_range": (15, 250)},
        {"base": "Tuyau PVC pression", "code_prefix": "TPVC", "price_range": (5, 60)},
        {"base": "Manchon acier", "code_prefix": "MAN", "price_range": (3, 40)},
        {"base": "Té égal acier", "code_prefix": "TEE", "price_range": (7, 100)},
        {"base": "Clapet anti-retour", "abbrev": "Clapet AR", "code_prefix": "CAR", "price_range": (20, 180)},
    ],
    "Composants Électriques": [
        {"base": "Câble électrique souple H07VK", "code_prefix": "CEL", "price_range": (1, 30)},
        {"base": "Disjoncteur modulaire", "abbrev": "Disj. mod.", "code_prefix": "DJM", "price_range": (10, 80)},
        {"base": "Contacteur tripolaire", "abbrev": "Cont. tri.", "code_prefix": "CTR", "price_range": (25, 200)},
        {"base": "Relais thermique", "abbrev": "Rel. therm.", "code_prefix": "RTH", "price_range": (20, 150)},
        {"base": "Bornier de raccordement", "code_prefix": "BOR", "price_range": (2, 25)},
        {"base": "Chemin de câbles", "abbrev": "Ch. câbles", "code_prefix": "CHC", "price_range": (8, 60)},
        {"base": "Presse-étoupe", "abbrev": "PE", "code_prefix": "PET", "price_range": (1, 12)},
        {"base": "Goulotte de câblage", "code_prefix": "GOU", "price_range": (5, 35)},
    ],
    "Équipements de Sécurité": [
        {"base": "Casque de chantier", "code_prefix": "CAS", "price_range": (5, 35)},
        {"base": "Lunettes de protection", "code_prefix": "LUN", "price_range": (3, 25)},
        {"base": "Gants de manutention", "code_prefix": "GMA", "price_range": (4, 30)},
        {"base": "Chaussures de sécurité S3", "code_prefix": "CHS", "price_range": (30, 120)},
        {"base": "Harnais antichute", "abbrev": "Harnais AC", "code_prefix": "HAC", "price_range": (50, 250)},
        {"base": "Gilet haute visibilité", "abbrev": "Gilet HV", "code_prefix": "GHV", "price_range": (5, 25)},
        {"base": "Masque respiratoire FFP2", "code_prefix": "MAS", "price_range": (2, 15)},
        {"base": "Bouchons d'oreilles", "code_prefix": "BOU", "price_range": (1, 8)},
    ],
    "Outillage Industriel": [
        {"base": "Clé dynamométrique", "abbrev": "Clé dynam.", "code_prefix": "CDY", "price_range": (30, 250)},
        {"base": "Perceuse à colonne", "code_prefix": "PAC", "price_range": (200, 1500)},
        {"base": "Meuleuse d'angle 125mm", "abbrev": "Meul. 125", "code_prefix": "MEU", "price_range": (40, 200)},
        {"base": "Poste à souder MIG/MAG", "abbrev": "Poste MIG", "code_prefix": "PSM", "price_range": (300, 2000)},
        {"base": "Scie à ruban", "code_prefix": "SAR", "price_range": (150, 1200)},
        {"base": "Pied à coulisse digital", "abbrev": "PAC digital", "code_prefix": "PCD", "price_range": (15, 120)},
    ],
    "Joints & Étanchéité": [
        {"base": "Joint plat NBR", "code_prefix": "JPN", "price_range": (1, 15)},
        {"base": "Joint torique Viton", "code_prefix": "JTV", "price_range": (0.5, 10)},
        {"base": "Presse-étoupe ATEX", "code_prefix": "PEA", "price_range": (5, 50)},
        {"base": "Tresse d'étanchéité PTFE", "abbrev": "Tresse PTFE", "code_prefix": "TPT", "price_range": (3, 30)},
        {"base": "Ruban téflon", "code_prefix": "RTF", "price_range": (1, 8)},
        {"base": "Mastic silicone haute température", "abbrev": "Mastic HT", "code_prefix": "MSH", "price_range": (5, 25)},
    ],
    "Peinture & Traitement de Surface": [
        {"base": "Peinture antirouille", "code_prefix": "PAR", "price_range": (10, 60)},
        {"base": "Primaire époxy bicomposant", "abbrev": "Prim. époxy", "code_prefix": "PEP", "price_range": (20, 120)},
        {"base": "Galvanisation à froid spray", "abbrev": "Galva spray", "code_prefix": "GSP", "price_range": (8, 30)},
        {"base": "Dégraissant industriel", "code_prefix": "DEG", "price_range": (5, 35)},
        {"base": "Convertisseur de rouille", "code_prefix": "CRO", "price_range": (8, 40)},
    ],
}

# Dimensional variants per category
DIMENSIONS = {
    "Acier & Métaux": ["2mm", "3mm", "4mm", "5mm", "6mm", "8mm", "10mm", "12mm", "15mm", "20mm"],
    "Boulonnerie & Fixations": ["M6x20", "M6x30", "M8x30", "M8x40", "M8x50", "M10x40", "M10x50", "M10x60", "M12x50", "M12x60", "M12x80", "M16x60", "M16x80", "M16x100", "M20x80", "M20x100"],
    "Tuyauterie & Raccords": ["DN15", "DN20", "DN25", "DN32", "DN40", "DN50", "DN65", "DN80", "DN100", "DN150", "DN200"],
    "Composants Électriques": ["1.5mm²", "2.5mm²", "4mm²", "6mm²", "10mm²", "16mm²", "25mm²"],
    "Équipements de Sécurité": ["S", "M", "L", "XL", "XXL", "Taille unique"],
    "Outillage Industriel": [],
    "Joints & Étanchéité": ["DN15", "DN20", "DN25", "DN32", "DN40", "DN50", "DN80", "DN100"],
    "Peinture & Traitement de Surface": ["0.5L", "1L", "2.5L", "5L", "20L"],
}

# Grade/class variants for fasteners
GRADES = ["4.8", "8.8", "10.9", "12.9", "A2-70", "A4-80"]

# HTML noise patterns for descriptions
HTML_DESCRIPTIONS = [
    "<p>Acier <b>haute résistance</b> conforme EN 10025</p>",
    "<div>Certification   ISO 9001<br/>Marquage CE</div>",
    "<p>Résistance à la corrosion : <i>excellente</i></p>\n<p>Température max : 400°C</p>",
    '<span style="color:red">ATTENTION</span> : Produit soumis à réglementation ATEX',
    "<p>Matière : acier inox 304L<br>Finition : poli miroir</p>",
    "<p>Conforme norme   NF EN 1092-1</p>  <p> </p>",
    "<ul><li>Usage intérieur</li><li>Usage extérieur</li></ul>",
    "Description\xa0: produit standard\xa0—\xa0voir fiche technique",
    "<p>  Livré avec certificat matière 3.1  </p>",
    "Pièce sur plan — délai selon quantité\r\n\r\nContactez le service commercial",
]

# Special/custom product names
SPECIAL_PRODUCTS = [
    "SUR MESURE - Plaque acier découpée",
    "SUR MESURE - Bride spéciale",
    "KIT - Boulonnerie complète bride DN100",
    "LOT - Visserie mixte chantier",
    "PROMO - Dégraissant industriel 5L (lot de 3)",
    "OBSOLÈTE - Ancien joint modèle K12",
    "À CONFIRMER - Tube spécial alliage Inconel 625",
    "REF CLIENT - Pièce spéciale #4587-B",
    "ESSAI - Prototype fixation rapide v2",
    "RECONDITIONNÉ - Vanne DN80 révisée",
]

random.seed(42)  # Reproducible generation


def name_variations(name: str, dim: str | None = None) -> list[str]:
    """Generate case/spacing variations of a product name."""
    full = f"{name} {dim}" if dim else name
    variations = [full]

    # Upper case
    variations.append(full.upper())

    # Compact (remove spaces around dimensions)
    if dim:
        compact = f"{name} {dim.replace(' ', '')}"
        variations.append(compact)
        # Hyphenated dimension
        if any(c.isdigit() for c in dim):
            variations.append(f"{name} {dim.replace(' ', '-')}")

    return variations


def generate_products(category_name: str, category_id: int, templates: list[dict]) -> list[dict]:
    """Generate product dicts for a category."""
    products = []

    for tmpl in templates:
        base_name = tmpl["base"]
        abbrev = tmpl.get("abbrev")
        code_prefix = tmpl["code_prefix"]
        price_min, price_max = tmpl["price_range"]

        dims = DIMENSIONS.get(category_name, [])
        if not dims:
            dims = [None]

        for dim in dims:
            # Full name
            name = f"{base_name} {dim}" if dim else base_name
            code = f"{code_prefix}-{dim}" if dim else code_prefix
            price = round(random.uniform(price_min, price_max), 2)

            product = {
                "name": name,
                "default_code": code,
                "list_price": price,
                "categ_id": category_id,
                "type": "consu",
                "sale_ok": True,
                "active": True,
                "description_sale": random.choice(HTML_DESCRIPTIONS) if random.random() < 0.3 else False,
            }

            # Randomly assign barcode (~60% of products)
            if random.random() < 0.6:
                product["barcode"] = f"34{random.randint(10000000000, 99999999999)}"

            products.append(product)

            # --- Noise: Duplicates with variations (~15% chance per product) ---
            if random.random() < 0.15:
                variations = name_variations(base_name, dim)
                dup_name = random.choice(variations[1:]) if len(variations) > 1 else name.upper()
                dup = product.copy()
                dup["name"] = dup_name
                # Duplicate may have slightly different or missing code
                if random.random() < 0.4:
                    dup["default_code"] = False
                else:
                    dup["default_code"] = f"{code_prefix}-{dim}-DUP" if dim else f"{code_prefix}-DUP"
                dup["barcode"] = False  # duplicates typically missing barcode
                products.append(dup)

            # --- Noise: Abbreviation variant (~20% for items with abbreviations) ---
            if abbrev and random.random() < 0.2:
                grade = random.choice(GRADES) if category_name == "Boulonnerie & Fixations" else ""
                abbrev_name = f"{abbrev} {grade} {dim}".strip() if dim else f"{abbrev} {grade}".strip()
                abbrev_product = product.copy()
                abbrev_product["name"] = abbrev_name
                abbrev_product["default_code"] = f"{code_prefix}-ABR-{dim}" if dim else f"{code_prefix}-ABR"
                abbrev_product["barcode"] = False  # avoid barcode uniqueness conflict
                products.append(abbrev_product)

        # --- Noise: Missing default_code variant ---
        if random.random() < 0.3:
            no_code = {
                "name": base_name,
                "default_code": False,
                "barcode": False,
                "list_price": round(random.uniform(price_min, price_max), 2),
                "categ_id": category_id,
                "type": "consu",
                "sale_ok": True,
                "active": True,
            }
            products.append(no_code)

    return products


def generate_non_proposable(category_ids: dict[str, int]) -> list[dict]:
    """Generate products with sale_ok=False or active=False."""
    products = []
    non_prop_items = [
        ("Ancien modèle - Vanne DN50 (OBSOLÈTE)", False, True),
        ("Câble 3G1.5 ANCIENNE REF", False, True),
        ("Joint NBR DN40 - REMPLACÉ", False, True),
        ("Bride PN16 DN80 - DÉCATALOGUÉ", False, True),
        ("Tube acier galva DN25 (ne plus vendre)", False, True),
        ("Clé mixte 13mm (retirée catalogue)", True, False),
        ("Gant nitrile bleu - ancien fournisseur", True, False),
        ("Mastic polyuréthane PU40 (archivé)", True, False),
        ("Perceuse colonne XR-200 (fin de série)", True, False),
        ("Profilé HEB 200 (stock épuisé définitivement)", True, False),
        ("Peinture RAL 7035 ancienne formule", False, False),
        ("Réduction DN100-DN50 inox (obsolète)", False, False),
    ]
    cat_names = list(category_ids.keys())
    for name, sale_ok, active in non_prop_items:
        cat = random.choice(cat_names)
        products.append({
            "name": name,
            "default_code": False,
            "barcode": False,
            "list_price": round(random.uniform(5, 200), 2),
            "categ_id": category_ids[cat],
            "type": "consu",
            "sale_ok": sale_ok,
            "active": active,
        })
    return products


def generate_special_products(category_ids: dict[str, int]) -> list[dict]:
    """Generate special/custom products."""
    products = []
    cat_names = list(category_ids.keys())
    for name in SPECIAL_PRODUCTS:
        cat = random.choice(cat_names)
        products.append({
            "name": name,
            "default_code": False,
            "barcode": False,
            "list_price": 0.0,
            "categ_id": category_ids[cat],
            "type": "consu",
            "sale_ok": True,
            "active": True,
            "description_sale": random.choice(HTML_DESCRIPTIONS),
        })
    return products


def main():
    print(f"Connecting to Odoo at {BASE_URL} (db={ODOO_DB}, user={ODOO_USER})...")
    rpc = OdooRPC(BASE_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
    print(f"Authenticated (uid={rpc.uid})")

    # --- Get existing product count ---
    existing_count = rpc.search_count("product.product")
    print(f"Existing products: {existing_count}")

    # --- Create categories ---
    print("\nCreating product categories...")
    category_ids: dict[str, int] = {}
    for cat_name in CATEGORIES:
        ids = rpc.create("product.category", [{"name": cat_name}])
        category_ids[cat_name] = ids[0]
        print(f"  Created category: {cat_name} (id={ids[0]})")

    # --- Generate all products ---
    all_products: list[dict] = []
    category_counts: dict[str, int] = {}

    for cat_name, templates in PRODUCT_TEMPLATES.items():
        cat_id = category_ids[cat_name]
        products = generate_products(cat_name, cat_id, templates)
        category_counts[cat_name] = len(products)
        all_products.extend(products)

    # Add non-proposable items
    non_prop = generate_non_proposable(category_ids)
    all_products.extend(non_prop)

    # Add special products
    specials = generate_special_products(category_ids)
    all_products.extend(specials)

    print(f"\nGenerated {len(all_products)} products total")

    # --- Batch create in Odoo (batches of 50 to avoid timeouts) ---
    BATCH_SIZE = 50
    created_ids: list[int] = []
    for i in range(0, len(all_products), BATCH_SIZE):
        batch = all_products[i : i + BATCH_SIZE]
        ids = rpc.create("product.product", batch)
        created_ids.extend(ids)
        print(f"  Created batch {i // BATCH_SIZE + 1}: {len(ids)} products (IDs {ids[0]}..{ids[-1]})")

    # --- Verify ---
    final_count = rpc.search_count("product.product")
    new_count = final_count - existing_count

    # Count noise breakdown
    dup_count = sum(1 for p in all_products if p.get("default_code") and "DUP" in str(p["default_code"]))
    abbr_count = sum(1 for p in all_products if p.get("default_code") and "ABR" in str(p["default_code"]))
    no_code_count = sum(1 for p in all_products if not p.get("default_code"))
    non_sale_count = sum(1 for p in all_products if not p.get("sale_ok", True))
    inactive_count = sum(1 for p in all_products if not p.get("active", True))
    html_desc_count = sum(1 for p in all_products if p.get("description_sale") and "<" in str(p.get("description_sale", "")))

    print(f"\n{'='*60}")
    print(f"SEED COMPLETE")
    print(f"{'='*60}")
    print(f"Products created:        {new_count}")
    print(f"Total products in Odoo:  {final_count}")
    print(f"\nBy category:")
    for cat_name, count in category_counts.items():
        print(f"  {cat_name}: {count}")
    print(f"  Non-proposable: {len(non_prop)}")
    print(f"  Special/Custom: {len(specials)}")
    print(f"\nNoise breakdown:")
    print(f"  Duplicates (name variations): {dup_count}")
    print(f"  Abbreviation variants:        {abbr_count}")
    print(f"  Missing default_code:         {no_code_count}")
    print(f"  Non-sellable (sale_ok=False):  {non_sale_count}")
    print(f"  Archived (active=False):       {inactive_count}")
    print(f"  HTML in descriptions:          {html_desc_count}")


if __name__ == "__main__":
    main()
