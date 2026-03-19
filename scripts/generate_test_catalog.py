"""Generate a realistic synthetic French industrial product catalog for testing.

Produces 50,000 product records in JSON Lines format with controlled noise
(missing metadata, duplicates, mixed languages, truncated fields, inconsistent casing)
to validate Epic 3 search and matching features against real-world conditions.

Usage:
    python scripts/generate_test_catalog.py
"""

from __future__ import annotations

import json
import random
import string
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# --- Constants ---

TOTAL_RECORDS = 50_000
SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
OUTPUT_FILE = OUTPUT_DIR / "catalog_50k.jsonl"
SAMPLE_FILE = OUTPUT_DIR / "catalog_50k_sample.jsonl"
SAMPLE_SIZE = 100

# Noise percentages
NOISE_MISSING_METADATA_PCT = 0.30
NOISE_DUPLICATE_PCT = 0.05
NOISE_MIXED_LANG_PCT = 0.10
NOISE_TRUNCATED_PCT = 0.05
NOISE_INCONSISTENT_CASE_PCT = 0.03
NOISE_INACTIVE_PCT = 0.02

# Stock status options
STOCK_STATUSES = ["in_stock", "out_of_stock", "on_order"]
STOCK_WEIGHTS = [0.70, 0.15, 0.15]

# Materials used across families
MATERIALS_METAL = ["INOX 304L", "INOX 316L", "ACIER S235", "ACIER S355", "GALVA", "CUIVRE", "LAITON", "ALU 6060"]
MATERIALS_SEAL = ["NBR", "VITON", "EPDM", "PTFE", "SILICONE"]
SUPPLIERS = [
    "SAINT-GOBAIN",
    "VALLOUREC",
    "ARCELOR",
    "SKF",
    "FAG",
    "SCHNEIDER",
    "LEGRAND",
    "PARKER",
    "BOSCH",
    "SIEMENS",
    "FACOM",
    "WURTH",
    "RS COMPONENTS",
    "MANUTAN",
    "OREXAD",
    "BERNER",
]
COUNTRIES = ["FR", "DE", "IT", "ES", "CN", "US", "JP", "BE", "NL", "SE"]


# --- Product Family Definitions ---


@dataclass
class ProductFamily:
    """Definition of a product family with generation templates."""

    name: str
    category: str
    weight: float  # proportion of total catalog
    ref_prefix: str
    name_templates: list[str]
    desc_template_fr: str
    desc_template_en: str
    materials: list[str]
    price_range: tuple[float, float]
    dimension_generator: str  # key into DIMENSION_GENERATORS


# Dimension generator functions
def _dim_tube(rng: random.Random) -> dict[str, Any]:
    diameter = rng.choice([10, 12, 15, 20, 25, 30, 32, 40, 50, 60, 80, 100, 125, 150, 200])
    thickness = rng.choice([1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0])
    length = rng.choice([1000, 2000, 3000, 6000])
    weight = round(diameter * thickness * length * 0.000025 * rng.uniform(0.8, 1.2), 2)
    return {
        "diameter": diameter,
        "thickness": thickness,
        "length": length,
        "weight_kg": weight,
        "dimensions": f"{diameter}x{thickness}x{length}",
    }


def _dim_fastener(rng: random.Random) -> dict[str, Any]:
    m_size = rng.choice([3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 24])
    length = rng.choice([8, 10, 12, 16, 20, 25, 30, 35, 40, 50, 60, 70, 80, 100])
    weight = round(m_size * length * 0.00005 * rng.uniform(0.8, 1.2), 3)
    return {"m_size": m_size, "length": length, "weight_kg": weight, "dimensions": f"M{m_size}x{length}"}


def _dim_plate(rng: random.Random) -> dict[str, Any]:
    width = rng.choice([500, 1000, 1250, 1500, 2000])
    height = rng.choice([1000, 2000, 2500, 3000])
    thickness = rng.choice([0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0])
    weight = round(width * height * thickness * 7.85e-6 * rng.uniform(0.9, 1.1), 1)
    return {
        "width": width,
        "height": height,
        "thickness": thickness,
        "weight_kg": weight,
        "dimensions": f"{width}x{height}x{thickness}",
    }


def _dim_profile(rng: random.Random) -> dict[str, Any]:
    size = rng.choice([80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 300])
    length = rng.choice([6000, 12000])
    weight_per_m = rng.uniform(5.0, 80.0)
    weight = round(weight_per_m * length / 1000, 1)
    return {"size": size, "length": length, "weight_kg": weight, "dimensions": f"IPE{size}-LG{length}"}


def _dim_fitting(rng: random.Random) -> dict[str, Any]:
    dn = rng.choice([8, 10, 15, 20, 25, 32, 40, 50, 65, 80, 100])
    weight = round(dn * 0.02 * rng.uniform(0.5, 2.0), 2)
    return {"dn": dn, "weight_kg": weight, "dimensions": f"DN{dn}"}


def _dim_bearing(rng: random.Random) -> dict[str, Any]:
    bore = rng.choice([6, 8, 10, 12, 15, 17, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80])
    od = bore + rng.choice([10, 14, 16, 20, 26, 32, 37, 42, 47, 52])
    width = rng.choice([5, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    weight = round(bore * od * width * 1e-5 * rng.uniform(0.5, 1.5), 3)
    return {"bore": bore, "od": od, "width": width, "weight_kg": weight, "dimensions": f"{bore}x{od}x{width}"}


def _dim_seal(rng: random.Random) -> dict[str, Any]:
    inner_d = rng.choice([3, 4, 5, 6, 8, 10, 12, 15, 18, 20, 22, 25, 30, 35, 40, 50, 60, 70, 80, 100])
    section = rng.choice([1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 5.7, 7.0])
    return {
        "inner_diameter": inner_d,
        "section": section,
        "weight_kg": round(rng.uniform(0.001, 0.05), 3),
        "dimensions": f"{inner_d}x{section}",
    }


def _dim_valve(rng: random.Random) -> dict[str, Any]:
    dn = rng.choice([10, 15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200])
    pn = rng.choice([6, 10, 16, 25, 40])
    weight = round(dn * pn * 0.005 * rng.uniform(0.5, 2.0), 1)
    return {"dn": dn, "pn": pn, "weight_kg": weight, "dimensions": f"DN{dn}-PN{pn}"}


def _dim_filter(rng: random.Random) -> dict[str, Any]:
    micron = rng.choice([1, 3, 5, 10, 20, 25, 40, 50, 75, 100])
    flow = rng.choice([10, 20, 40, 60, 80, 100, 150, 200])
    return {
        "micron_rating": micron,
        "flow_lpm": flow,
        "weight_kg": round(rng.uniform(0.1, 5.0), 2),
        "dimensions": f"{micron}um-{flow}L/min",
    }


def _dim_cable(rng: random.Random) -> dict[str, Any]:
    section = rng.choice([0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0])
    cores = rng.choice([1, 2, 3, 4, 5, 7, 12, 19])
    length = rng.choice([50, 100, 200, 500, 1000])
    weight = round(section * cores * length * 0.01 * rng.uniform(0.8, 1.2), 1)
    return {
        "section_mm2": section,
        "cores": cores,
        "length_m": length,
        "weight_kg": weight,
        "dimensions": f"{cores}x{section}mm2-{length}m",
    }


def _dim_cutting_tool(rng: random.Random) -> dict[str, Any]:
    diameter = rng.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0])
    length = rng.choice([30, 40, 50, 60, 70, 80, 100, 120, 150])
    return {
        "diameter": diameter,
        "length": length,
        "weight_kg": round(rng.uniform(0.01, 0.5), 3),
        "dimensions": f"D{diameter}xL{length}",
    }


def _dim_abrasive(rng: random.Random) -> dict[str, Any]:
    diameter = rng.choice([115, 125, 150, 180, 230, 300, 350])
    thickness = rng.choice([1.0, 1.6, 2.0, 3.0, 6.0, 7.0])
    grain = rng.choice([24, 36, 40, 60, 80, 120, 180, 240, 320])
    return {
        "diameter": diameter,
        "thickness": thickness,
        "grain": grain,
        "weight_kg": round(rng.uniform(0.05, 1.0), 2),
        "dimensions": f"{diameter}x{thickness}-P{grain}",
    }


def _dim_lubricant(rng: random.Random) -> dict[str, Any]:
    volume = rng.choice([0.4, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0, 208.0])
    viscosity = rng.choice(["5W30", "10W40", "15W40", "ISO VG 32", "ISO VG 46", "ISO VG 68", "ISO VG 100", "NLGI 2"])
    return {
        "volume_l": volume,
        "viscosity": viscosity,
        "weight_kg": round(volume * 0.88 * rng.uniform(0.9, 1.1), 1),
        "dimensions": f"{volume}L",
    }


def _dim_ppe(rng: random.Random) -> dict[str, Any]:
    size = rng.choice(["XS", "S", "M", "L", "XL", "XXL", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"])
    return {"size": size, "weight_kg": round(rng.uniform(0.05, 2.0), 2)}


def _dim_hardware(rng: random.Random) -> dict[str, Any]:
    return {
        "weight_kg": round(rng.uniform(0.01, 3.0), 2),
        "dimensions": f"{rng.randint(10, 300)}x{rng.randint(10, 300)}",
    }


DIMENSION_GENERATORS: dict[str, Any] = {
    "tube": _dim_tube,
    "fastener": _dim_fastener,
    "plate": _dim_plate,
    "profile": _dim_profile,
    "fitting": _dim_fitting,
    "bearing": _dim_bearing,
    "seal": _dim_seal,
    "valve": _dim_valve,
    "filter": _dim_filter,
    "cable": _dim_cable,
    "cutting_tool": _dim_cutting_tool,
    "abrasive": _dim_abrasive,
    "lubricant": _dim_lubricant,
    "ppe": _dim_ppe,
    "hardware": _dim_hardware,
}


FAMILIES: list[ProductFamily] = [
    ProductFamily(
        name="tubes",
        category="Tubes & Tuyaux",
        weight=0.15,
        ref_prefix="TB",
        name_templates=[
            "TB {shape} {material} {diameter}x{thickness} LG{length}",
            "TUBE {shape} {material} DN{diameter} EP{thickness} L{length}",
        ],
        desc_template_fr=(
            "Tube {shape_fr} en {material_fr}, diametre {diameter}mm, epaisseur {thickness}mm, longueur {length}mm"
        ),
        desc_template_en="Round tube {material}, diameter {diameter}mm, thickness {thickness}mm, length {length}mm",
        materials=MATERIALS_METAL,
        price_range=(5.0, 350.0),
        dimension_generator="tube",
    ),
    ProductFamily(
        name="fasteners",
        category="Boulonnerie & Visserie",
        weight=0.15,
        ref_prefix="VIS",
        name_templates=[
            "VIS {head_type} {material} M{m_size}x{length}",
            "{head_type} {material} M{m_size}x{length} CL{cls}",
            "ECR HM {material} M{m_size}",
            "RDL {material} M{m_size}",
        ],
        desc_template_fr="Vis {head_type_fr} {material}, M{m_size}x{length}, classe {cls}",
        desc_template_en="{head_type} screw {material} M{m_size}x{length} class {cls}",
        materials=[*MATERIALS_METAL[:4], "INOX A2", "INOX A4", "ZINGUE", "BRUNI"],
        price_range=(0.02, 15.0),
        dimension_generator="fastener",
    ),
    ProductFamily(
        name="plates",
        category="Toles & Plaques",
        weight=0.10,
        ref_prefix="TL",
        name_templates=[
            "TOLE {material} {width}x{height} EP{thickness}",
            "TL {finish} {material} {width}x{height}x{thickness}",
            "PLAQUE {material} EP{thickness} {width}x{height}",
        ],
        desc_template_fr="Tole {finish_fr} en {material_fr}, {width}x{height}mm, epaisseur {thickness}mm",
        desc_template_en="Sheet {material} {width}x{height}mm thickness {thickness}mm",
        materials=MATERIALS_METAL,
        price_range=(15.0, 1200.0),
        dimension_generator="plate",
    ),
    ProductFamily(
        name="profiles",
        category="Profiles",
        weight=0.08,
        ref_prefix="PRF",
        name_templates=[
            "IPE {size} S235 LG{length}",
            "HEA {size} S355 LG{length}",
            "CORNIERE {material} {size}x{size} LG{length}",
            "FER U {size} {material} LG{length}",
        ],
        desc_template_fr="Profile IPE {size}, acier S235, longueur {length}mm",
        desc_template_en="IPE {size} steel profile, length {length}mm",
        materials=["ACIER S235", "ACIER S355"],
        price_range=(30.0, 800.0),
        dimension_generator="profile",
    ),
    ProductFamily(
        name="fittings",
        category="Raccords",
        weight=0.08,
        ref_prefix="RAC",
        name_templates=[
            "RAC {type} {material} DN{dn}",
            "RACCORD {type} {material} DN{dn} {threading}",
            "MAMELON {material} DN{dn}",
        ],
        desc_template_fr="Raccord {type_fr} en {material_fr}, DN{dn}",
        desc_template_en="{type} fitting {material} DN{dn}",
        materials=[*MATERIALS_METAL[:4], "PVC", "PPR", "FONTE"],
        price_range=(1.0, 120.0),
        dimension_generator="fitting",
    ),
    ProductFamily(
        name="bearings",
        category="Roulements",
        weight=0.07,
        ref_prefix="RLT",
        name_templates=[
            "RLT {type} {bore}x{od}x{width}",
            "ROULEMENT {type} {designation}",
            "{brand} {designation} {type}",
        ],
        desc_template_fr="Roulement a {type_fr} {bore}x{od}x{width}mm",
        desc_template_en="{type} bearing {bore}x{od}x{width}mm",
        materials=["ACIER CHROME", "ACIER INOX", "CERAMIQUE"],
        price_range=(2.0, 500.0),
        dimension_generator="bearing",
    ),
    ProductFamily(
        name="seals",
        category="Joints & Etancheite",
        weight=0.06,
        ref_prefix="JNT",
        name_templates=[
            "JNT TOR {material} {inner_diameter}x{section}",
            "JOINT PLAT {material} DN{inner_diameter}",
            "TRESSE {material} {inner_diameter}mm",
        ],
        desc_template_fr="Joint torique en {material}, {inner_diameter}x{section}mm",
        desc_template_en="O-ring {material} {inner_diameter}x{section}mm",
        materials=MATERIALS_SEAL,
        price_range=(0.10, 45.0),
        dimension_generator="seal",
    ),
    ProductFamily(
        name="valves",
        category="Vannes & Robinetterie",
        weight=0.06,
        ref_prefix="VAN",
        name_templates=[
            "VANNE {type} {material} DN{dn} PN{pn}",
            "VAN {type} DN{dn} PN{pn} {actuation}",
            "CLAPET {material} DN{dn} PN{pn}",
        ],
        desc_template_fr="Vanne {type_fr} en {material_fr}, DN{dn}, PN{pn}",
        desc_template_en="{type} valve {material} DN{dn} PN{pn}",
        materials=["INOX 316L", "FONTE", "LAITON", "BRONZE", "PVC"],
        price_range=(8.0, 2500.0),
        dimension_generator="valve",
    ),
    ProductFamily(
        name="filtration",
        category="Filtration",
        weight=0.05,
        ref_prefix="FLT",
        name_templates=[
            "FILTRE {type} {micron}um {flow}L/min",
            "FLT {type} {micron}UM DEBIT{flow}",
            "CARTOUCHE FILTRANTE {micron}um",
        ],
        desc_template_fr="Filtre {type_fr}, {micron} microns, debit {flow} L/min",
        desc_template_en="{type} filter {micron} micron, flow rate {flow} L/min",
        materials=["INOX 316L", "PAPIER", "POLYESTER", "CELLULOSE"],
        price_range=(3.0, 350.0),
        dimension_generator="filter",
    ),
    ProductFamily(
        name="electrical",
        category="Electrique & Cables",
        weight=0.05,
        ref_prefix="CAB",
        name_templates=[
            "CABLE {type} {cores}x{section_mm2}mm2 {length_m}m",
            "CAB {type} {cores}G{section_mm2} L{length_m}M",
            "GAINE {type} D{section_mm2}",
        ],
        desc_template_fr="Cable {type} {cores}x{section_mm2}mm2, longueur {length_m}m",
        desc_template_en="{type} cable {cores}x{section_mm2}mm2, {length_m}m length",
        materials=["CUIVRE", "ALU", "CUIVRE ETAME"],
        price_range=(5.0, 800.0),
        dimension_generator="cable",
    ),
    ProductFamily(
        name="cutting_tools",
        category="Outils de Coupe",
        weight=0.04,
        ref_prefix="OC",
        name_templates=[
            "FORET {material} D{diameter} L{length}",
            "FRAISE {type} {material} D{diameter}",
            "PLAQUETTE {type} {material}",
        ],
        desc_template_fr="Foret en {material_fr}, diametre {diameter}mm, longueur {length}mm",
        desc_template_en="Drill bit {material} D{diameter}mm L{length}mm",
        materials=["HSS", "HSS-CO", "CARBURE", "CARBURE REVETU"],
        price_range=(1.0, 180.0),
        dimension_generator="cutting_tool",
    ),
    ProductFamily(
        name="abrasives",
        category="Abrasifs",
        weight=0.03,
        ref_prefix="ABR",
        name_templates=[
            "DISQUE {type} {diameter}x{thickness} P{grain}",
            "ABR {type} D{diameter} GRAIN{grain}",
            "MEULE {type} {diameter}x{thickness}",
        ],
        desc_template_fr="Disque {type_fr} {diameter}mm, grain P{grain}",
        desc_template_en="{type} disc {diameter}mm grain P{grain}",
        materials=["CORINDON", "ZIRCONIUM", "CERAMIQUE", "DIAMANT"],
        price_range=(0.50, 45.0),
        dimension_generator="abrasive",
    ),
    ProductFamily(
        name="lubricants",
        category="Lubrifiants",
        weight=0.03,
        ref_prefix="LUB",
        name_templates=[
            "HUILE {type} {viscosity} {volume_l}L",
            "LUB {type} {viscosity} BIDON {volume_l}L",
            "GRAISSE {type} {volume_l}KG",
        ],
        desc_template_fr="Huile {type_fr}, viscosite {viscosity}, bidon de {volume_l} litres",
        desc_template_en="{type} oil {viscosity}, {volume_l}L container",
        materials=["MINERALE", "SYNTHETIQUE", "SEMI-SYNTH"],
        price_range=(5.0, 600.0),
        dimension_generator="lubricant",
    ),
    ProductFamily(
        name="ppe",
        category="EPI & Securite",
        weight=0.03,
        ref_prefix="EPI",
        name_templates=[
            "GANT {type} TAILLE {size}",
            "EPI {type} T{size}",
            "LUNETTE {type} {color}",
            "CHAUSSURE SECURITE {type} P{size}",
        ],
        desc_template_fr="Gant de protection {type_fr}, taille {size}",
        desc_template_en="{type} safety glove, size {size}",
        materials=["NITRILE", "LATEX", "CUIR", "POLYCARB", "S3 SRC"],
        price_range=(2.0, 120.0),
        dimension_generator="ppe",
    ),
    ProductFamily(
        name="hardware",
        category="Quincaillerie",
        weight=0.02,
        ref_prefix="QNC",
        name_templates=[
            "CHARNIERE {type} {material}",
            "POIGNEE {type} {material} L{dimensions}",
            "SERRURE {type} {material}",
            "QNC {type} {material}",
        ],
        desc_template_fr="Quincaillerie {type_fr} en {material_fr}",
        desc_template_en="{type} hardware, {material}",
        materials=["INOX", "ACIER ZINGUE", "LAITON", "ZAMAK", "ALU"],
        price_range=(1.0, 85.0),
        dimension_generator="hardware",
    ),
]


# --- Product Record ---


@dataclass
class ProductRecord:
    """A single product catalog entry."""

    reference: str
    name: str
    description: str | None
    category: str
    unit_price: float
    stock_status: str
    is_active: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return asdict(self)


# --- Generator Logic ---

# Sub-attributes for product name generation
TUBE_SHAPES = ["RD", "CR", "RECT", "OBLONG"]
TUBE_SHAPES_FR = {"RD": "rond", "CR": "carre", "RECT": "rectangulaire", "OBLONG": "oblong"}
FASTENER_HEADS = ["CHC", "HM", "FHC", "BTR", "TF", "TB"]
FASTENER_HEADS_FR = {
    "CHC": "cylindrique creuse",
    "HM": "hexagonale",
    "FHC": "fraisee",
    "BTR": "BTR",
    "TF": "tete fraisee",
    "TB": "tete bombee",
}
FASTENER_CLASSES = ["4.8", "8.8", "10.9", "12.9", "A2-70", "A4-80"]
FITTING_TYPES = ["COUDE", "TE", "REDUCTION", "MANCHON", "UNION"]
FITTING_TYPES_FR = {"COUDE": "coude", "TE": "te", "REDUCTION": "reduction", "MANCHON": "manchon", "UNION": "union"}
FITTING_THREADINGS = ["M/M", "F/F", "M/F", "BSP", "NPT"]
BEARING_TYPES = ["BILLES", "ROULEAUX", "AIGUILLES", "BUTEE"]
BEARING_TYPES_FR = {"BILLES": "billes", "ROULEAUX": "rouleaux coniques", "AIGUILLES": "aiguilles", "BUTEE": "butee"}
BEARING_BRANDS = ["SKF", "FAG", "NTN", "TIMKEN", "NSK", "INA"]
VALVE_TYPES = ["PAPILLON", "BILLE", "VANNE", "CLAPET"]
VALVE_TYPES_FR = {"PAPILLON": "papillon", "BILLE": "a bille", "VANNE": "a opercule", "CLAPET": "anti-retour"}
VALVE_ACTUATIONS = ["MANUELLE", "PNEUM", "ELEC", "HYDRAUL"]
FILTER_TYPES = ["HYDRAULIQUE", "PNEUMATIQUE", "AIR", "HUILE"]
FILTER_TYPES_FR = {"HYDRAULIQUE": "hydraulique", "PNEUMATIQUE": "pneumatique", "AIR": "a air", "HUILE": "a huile"}
CABLE_TYPES = ["H07VK", "H07RNF", "U1000R2V", "LIYCY", "OLFLEX"]
CUTTING_TYPES = ["HELICOIDAL", "CARBURE", "QUEUE CYLINDRIQUE"]
ABRASIVE_TYPES = ["TRONCONNAGE", "EBAVURAGE", "LAMELLE", "FIBRE"]
ABRASIVE_TYPES_FR = {"TRONCONNAGE": "a tronconner", "EBAVURAGE": "a ebarber", "LAMELLE": "a lamelles", "FIBRE": "fibre"}
LUBRICANT_TYPES = ["MOTEUR", "HYDRAULIQUE", "ENGRENAGE", "COUPE", "MULTIUSAGE"]
LUBRICANT_TYPES_FR = {
    "MOTEUR": "moteur",
    "HYDRAULIQUE": "hydraulique",
    "ENGRENAGE": "pour engrenages",
    "COUPE": "de coupe",
    "MULTIUSAGE": "multiusage",
}
PPE_TYPES = ["NITRILE", "LATEX", "CUIR", "ANTI-COUPURE", "POLYCARBONATE", "S3 SRC"]
PPE_COLORS = ["CLAIR", "FUME", "JAUNE", "INCOLORE"]
HARDWARE_TYPES = ["PIANO", "INVISIBLE", "EQUERRE", "TUBULAIRE", "CYLINDRIQUE", "BATIMENT"]
PLATE_FINISHES = ["LAMINEE", "DECAPEE", "POLIE", "BRUTE"]
PLATE_FINISHES_FR = {"LAMINEE": "laminee a chaud", "DECAPEE": "decapee", "POLIE": "polie miroir", "BRUTE": "brute"}
MATERIAL_FR = {
    "INOX 304L": "acier inoxydable 304L",
    "INOX 316L": "acier inoxydable 316L",
    "ACIER S235": "acier S235",
    "ACIER S355": "acier S355",
    "GALVA": "acier galvanise",
    "CUIVRE": "cuivre",
    "LAITON": "laiton",
    "ALU 6060": "aluminium 6060",
    "INOX A2": "inox A2",
    "INOX A4": "inox A4",
    "ZINGUE": "acier zingue",
    "BRUNI": "acier bruni",
    "FONTE": "fonte",
    "BRONZE": "bronze",
    "PVC": "PVC",
    "PPR": "polypropylene",
    "INOX": "inox",
    "ACIER ZINGUE": "acier zingue",
    "ZAMAK": "zamak",
    "ALU": "aluminium",
}


def _generate_reference(rng: random.Random, family: ProductFamily, dims: dict[str, Any], seq: int) -> str:
    """Generate a realistic reference code for a product."""
    prefix = family.ref_prefix
    parts = [prefix]

    if family.name == "tubes":
        shape = rng.choice(TUBE_SHAPES)
        material_short = dims.get("_material_short", "INOX")
        parts.extend([shape, material_short, f"{dims['diameter']}x{dims['thickness']}", f"LG{dims['length']}"])
    elif family.name == "fasteners":
        head = rng.choice(FASTENER_HEADS)
        parts.extend([head, f"M{dims['m_size']}x{dims['length']}"])
    elif family.name == "plates":
        parts.extend([f"{dims['width']}x{dims['height']}", f"EP{dims['thickness']}"])
    elif family.name == "profiles":
        parts.append(dims["dimensions"])
    elif family.name == "fittings":
        ft = rng.choice(FITTING_TYPES)
        parts.extend([ft, f"DN{dims['dn']}"])
    elif family.name == "bearings":
        parts.append(dims["dimensions"])
    elif family.name == "seals":
        parts.append(f"{dims['inner_diameter']}x{dims['section']}")
    elif family.name == "valves":
        vt = rng.choice(VALVE_TYPES)
        parts.extend([vt, dims["dimensions"]])
    elif family.name == "filtration":
        parts.append(dims["dimensions"])
    elif family.name == "electrical":
        parts.append(f"{dims.get('cores', 3)}x{dims.get('section_mm2', 1.5)}")
    elif family.name in ("cutting_tools", "abrasives", "lubricants"):
        parts.append(dims["dimensions"])
    elif family.name == "ppe":
        parts.append(str(dims.get("size", "L")))
    elif family.name == "hardware":
        parts.append(str(seq).zfill(4))

    # Add unique suffix to avoid collisions
    suffix = "".join(rng.choices(string.ascii_uppercase + string.digits, k=3))
    parts.append(suffix)
    return "-".join(parts)


def _generate_name(rng: random.Random, family: ProductFamily, dims: dict[str, Any], material: str) -> str:
    """Generate a realistic abbreviated French product name."""
    template = rng.choice(family.name_templates)
    shape = rng.choice(TUBE_SHAPES) if family.name == "tubes" else ""
    head_type = rng.choice(FASTENER_HEADS) if family.name == "fasteners" else ""
    cls = rng.choice(FASTENER_CLASSES) if family.name == "fasteners" else ""
    ft = rng.choice(FITTING_TYPES) if family.name == "fittings" else ""
    threading = rng.choice(FITTING_THREADINGS) if family.name == "fittings" else ""
    bt = rng.choice(BEARING_TYPES) if family.name == "bearings" else ""
    brand = rng.choice(BEARING_BRANDS) if family.name == "bearings" else ""
    vt = rng.choice(VALVE_TYPES) if family.name == "valves" else ""
    actuation = rng.choice(VALVE_ACTUATIONS) if family.name == "valves" else ""
    filt = rng.choice(FILTER_TYPES) if family.name == "filtration" else ""
    cab = rng.choice(CABLE_TYPES) if family.name == "electrical" else ""
    ct = rng.choice(CUTTING_TYPES) if family.name == "cutting_tools" else ""
    abr = rng.choice(ABRASIVE_TYPES) if family.name == "abrasives" else ""
    lub = rng.choice(LUBRICANT_TYPES) if family.name == "lubricants" else ""
    ppe_type = rng.choice(PPE_TYPES) if family.name == "ppe" else ""
    color = rng.choice(PPE_COLORS) if family.name == "ppe" else ""
    hw = rng.choice(HARDWARE_TYPES) if family.name == "hardware" else ""
    finish = rng.choice(PLATE_FINISHES) if family.name == "plates" else ""
    designation = f"{dims.get('bore', '')}{'0' + str(dims.get('od', ''))[-2:]}" if family.name == "bearings" else ""

    # Build a format dict from all possible values
    fmt: dict[str, Any] = {
        **dims,
        "material": material,
        "shape": shape,
        "head_type": head_type,
        "cls": cls,
        "type": ft or bt or vt or filt or cab or ct or abr or lub or ppe_type or hw,
        "threading": threading,
        "brand": brand,
        "designation": designation,
        "actuation": actuation,
        "color": color,
        "finish": finish,
    }

    try:
        return template.format_map(SafeFormatDict(fmt))
    except (KeyError, ValueError):
        # Fallback: simple name
        return f"{family.ref_prefix} {material} {dims.get('dimensions', '')}"


class SafeFormatDict(dict[str, Any]):
    """Dict that returns the key name for missing format keys."""

    def __missing__(self, key: str) -> str:
        return ""


def _generate_description(
    rng: random.Random,
    family: ProductFamily,
    dims: dict[str, Any],
    material: str,
    use_english: bool,
) -> str:
    """Generate a product description in French or English."""
    template = family.desc_template_en if use_english else family.desc_template_fr

    # Build format context
    material_fr = MATERIAL_FR.get(material, material.lower())

    fmt: dict[str, Any] = {
        **dims,
        "material": material,
        "material_fr": material_fr,
        "shape_fr": TUBE_SHAPES_FR.get(rng.choice(TUBE_SHAPES), "rond"),
        "head_type_fr": FASTENER_HEADS_FR.get(rng.choice(FASTENER_HEADS), "hexagonale"),
        "type_fr": "",
        "finish_fr": PLATE_FINISHES_FR.get(rng.choice(PLATE_FINISHES), "brute"),
        "finish": rng.choice(PLATE_FINISHES),
    }

    # Set type_fr based on family
    if family.name == "fittings":
        ft = rng.choice(FITTING_TYPES)
        fmt["type_fr"] = FITTING_TYPES_FR.get(ft, ft.lower())
        fmt["type"] = ft
    elif family.name == "bearings":
        bt = rng.choice(BEARING_TYPES)
        fmt["type_fr"] = BEARING_TYPES_FR.get(bt, bt.lower())
        fmt["type"] = bt
    elif family.name == "valves":
        vt = rng.choice(VALVE_TYPES)
        fmt["type_fr"] = VALVE_TYPES_FR.get(vt, vt.lower())
        fmt["type"] = vt
    elif family.name == "filtration":
        filt = rng.choice(FILTER_TYPES)
        fmt["type_fr"] = FILTER_TYPES_FR.get(filt, filt.lower())
        fmt["type"] = filt
    elif family.name == "abrasives":
        abr = rng.choice(ABRASIVE_TYPES)
        fmt["type_fr"] = ABRASIVE_TYPES_FR.get(abr, abr.lower())
        fmt["type"] = abr
    elif family.name == "lubricants":
        lub = rng.choice(LUBRICANT_TYPES)
        fmt["type_fr"] = LUBRICANT_TYPES_FR.get(lub, lub.lower())
        fmt["type"] = lub
    else:
        fmt["type_fr"] = family.name
        fmt["type"] = family.name

    try:
        return template.format_map(SafeFormatDict(fmt))
    except (KeyError, ValueError):
        return f"{family.category} - {material}"


def _apply_case_noise(rng: random.Random, text: str) -> str:
    """Apply random casing noise."""
    choice = rng.random()
    if choice < 0.4:
        return text.upper()
    elif choice < 0.7:
        return text.lower()
    else:
        return text.title()


def _truncate(rng: random.Random, text: str) -> str:
    """Truncate a string at a random point."""
    if len(text) <= 10:
        return text
    cut = rng.randint(10, max(10, len(text) - 5))
    return text[:cut]


def generate_catalog(total: int = TOTAL_RECORDS, seed: int = SEED) -> list[ProductRecord]:
    """Generate the full synthetic catalog."""
    rng = random.Random(seed)

    # Calculate per-family counts
    family_counts: list[tuple[ProductFamily, int]] = []
    allocated = 0
    for i, fam in enumerate(FAMILIES):
        count = total - allocated if i == len(FAMILIES) - 1 else round(total * fam.weight)
        family_counts.append((fam, count))
        allocated += count

    records: list[ProductRecord] = []
    duplicates_to_add: list[ProductRecord] = []

    for family, count in family_counts:
        dim_gen = DIMENSION_GENERATORS[family.dimension_generator]

        for seq in range(count):
            dims = dim_gen(rng)
            material = rng.choice(family.materials)

            # Store short material name for reference generation
            mat_short = material.replace(" ", "").replace("-", "")[:8]
            dims["_material_short"] = mat_short

            reference = _generate_reference(rng, family, dims, seq)
            name = _generate_name(rng, family, dims, material)

            # Description: ~10% English, ~5% None (missing), rest French
            use_english = rng.random() < NOISE_MIXED_LANG_PCT
            desc: str | None = (
                None if rng.random() < 0.05 else _generate_description(rng, family, dims, material, use_english)
            )

            # Truncated description (~5% of non-None descriptions)
            if desc is not None and rng.random() < NOISE_TRUNCATED_PCT:
                desc = _truncate(rng, desc)

            # Inconsistent casing (~3%)
            if rng.random() < NOISE_INCONSISTENT_CASE_PCT:
                name = _apply_case_noise(rng, name)

            # Price
            price = round(rng.uniform(*family.price_range), 2)

            # Stock status
            stock = rng.choices(STOCK_STATUSES, weights=STOCK_WEIGHTS, k=1)[0]

            # Active status (~2% inactive)
            is_active = rng.random() >= NOISE_INACTIVE_PCT

            # Metadata with controlled missing fields (~30% have some missing fields)
            metadata: dict[str, Any] = {}
            optional_meta_fields = {
                "weight_kg": dims.get("weight_kg"),
                "dimensions": dims.get("dimensions"),
                "material": material,
                "supplier": rng.choice(SUPPLIERS),
                "country_of_origin": rng.choice(COUNTRIES),
                "min_order_qty": rng.choice([1, 5, 10, 25, 50, 100]),
                "lead_time_days": rng.choice([0, 1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60]),
            }

            for meta_key, meta_val in optional_meta_fields.items():
                if meta_val is not None and rng.random() >= NOISE_MISSING_METADATA_PCT:
                    metadata[meta_key] = meta_val

            record = ProductRecord(
                reference=reference,
                name=name,
                description=desc,
                category=family.category,
                unit_price=price,
                stock_status=stock,
                is_active=is_active,
                metadata=metadata,
            )
            records.append(record)

            # Collect candidates for duplication (~5% of records)
            if rng.random() < NOISE_DUPLICATE_PCT:
                # Create variant with slightly different name
                variant_name = _create_variant_name(rng, name, material)
                dup = ProductRecord(
                    reference=reference + "-VAR",
                    name=variant_name,
                    description=record.description,
                    category=record.category,
                    unit_price=round(price * rng.uniform(0.98, 1.02), 2),  # slight price variation
                    stock_status=record.stock_status,
                    is_active=record.is_active,
                    metadata=dict(record.metadata),
                )
                duplicates_to_add.append(dup)

    # Insert duplicates at random positions (they replace records to maintain total count)
    # We need exactly `total` records, so replace last N records with duplicates
    num_dups = min(len(duplicates_to_add), total // 20)  # cap at ~5%
    if num_dups > 0:
        # Replace records at random positions
        positions = rng.sample(range(len(records)), num_dups)
        for i, pos in enumerate(positions):
            records[pos] = duplicates_to_add[i]

    # Shuffle to mix families
    rng.shuffle(records)

    return records


def _create_variant_name(rng: random.Random, original: str, material: str) -> str:
    """Create a duplicate product name with variation (abbreviation differences)."""
    variants = [
        # French to English abbreviation
        ("TUBE ROND", "TB RD"),
        ("INOX 304L", "SS 304L"),
        ("INOX 316L", "SS 316L"),
        ("ACIER", "STEEL"),
        ("GALVA", "GALVANIZED"),
        ("ROULEMENT", "BEARING"),
        ("JOINT", "SEAL"),
        ("VANNE", "VALVE"),
        # Short to long
        ("TB", "TUBE"),
        ("VIS", "SCREW"),
        ("ECR", "ECROU"),
        ("RDL", "RONDELLE"),
        ("RAC", "RACCORD"),
        ("FLT", "FILTRE"),
        ("CAB", "CABLE"),
    ]

    result = original
    for fr_form, alt_form in variants:
        if fr_form in result:
            result = result.replace(fr_form, alt_form, 1)
            break

    # If no variant applied, just change casing
    if result == original:
        result = _apply_case_noise(rng, original)

    return result


def write_catalog(records: list[ProductRecord], output_path: Path, sample_path: Path, sample_size: int) -> None:
    """Write catalog to JSONL files."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    with open(sample_path, "w", encoding="utf-8") as f:
        for record in records[:sample_size]:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def compute_stats(records: list[ProductRecord]) -> dict[str, Any]:
    """Compute generation statistics."""
    total = len(records)

    # Category distribution
    cat_counts: dict[str, int] = {}
    for r in records:
        cat_counts[r.category] = cat_counts.get(r.category, 0) + 1

    # Noise stats
    missing_meta_count = sum(1 for r in records if len(r.metadata) < 4)  # less than half of 7 optional fields
    inactive_count = sum(1 for r in records if not r.is_active)
    null_desc_count = sum(1 for r in records if r.description is None)

    # Detect duplicates by looking for -VAR suffix in references
    dup_count = sum(1 for r in records if r.reference.endswith("-VAR"))

    return {
        "total_records": total,
        "categories": {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in sorted(cat_counts.items())},
        "noise": {
            "missing_metadata_pct": round(missing_meta_count / total * 100, 1),
            "inactive_pct": round(inactive_count / total * 100, 1),
            "null_description_pct": round(null_desc_count / total * 100, 1),
            "duplicate_variant_count": dup_count,
            "duplicate_variant_pct": round(dup_count / total * 100, 1),
        },
    }


def print_stats(stats: dict[str, Any]) -> None:
    """Print generation statistics to stdout."""
    sep = "=" * 60
    print(f"\n{sep}")
    print("  Catalog Generation Complete")
    print(sep)
    print(f"  Total records: {stats['total_records']:,}")
    print("\n  Category Distribution:")
    for cat, info in stats["categories"].items():
        print(f"    {cat:<30} {info['count']:>6,} ({info['pct']:>5.1f}%)")
    print("\n  Noise Distribution:")
    noise = stats["noise"]
    print(f"    Missing metadata (< 4 fields): {noise['missing_metadata_pct']:.1f}%")
    print(f"    Inactive products:             {noise['inactive_pct']:.1f}%")
    print(f"    Null descriptions:             {noise['null_description_pct']:.1f}%")
    dup_count = noise["duplicate_variant_count"]
    dup_pct = noise["duplicate_variant_pct"]
    print(f"    Duplicate variants:            {dup_count:,} ({dup_pct:.1f}%)")
    print(f"{sep}\n")


def main() -> None:
    """Generate the test catalog and write to disk."""
    print("Generating 50,000 product catalog with seed=42...")
    records = generate_catalog()
    print(f"Generated {len(records):,} records.")

    write_catalog(records, OUTPUT_FILE, SAMPLE_FILE, SAMPLE_SIZE)
    print(f"Written to {OUTPUT_FILE}")
    print(f"Sample written to {SAMPLE_FILE} ({SAMPLE_SIZE} records)")

    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"File size: {file_size_mb:.1f} MB")
    if file_size_mb > 50:
        print("WARNING: File exceeds 50MB — consider Git LFS tracking")

    stats = compute_stats(records)
    print_stats(stats)


if __name__ == "__main__":
    main()
