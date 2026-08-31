"""
SYCSAtech - CALCULADOR DE CICLONES V19
=====================================

Aplicación gráfica multipágina para prediseño de ciclones.

CARACTERÍSTICAS
---------------
- Interfaz tipo software de ingeniería.
- Navegación lateral por módulos.
- Branding SYCSAtech.
- Logo externo SYCSA_TECH_logo.png.
- Datos de proceso con unidades flexibles.
- Biblioteca de materiales.
- Distribución granulométrica única o log-normal.
- Geometrías Stairmand (EPA) y Lapple.
- Cálculo de velocidad de entrada, can velocity y Reynolds.
- Diámetro de corte y eficiencia fraccional/global.
- Pérdida de presión aproximada.
- Comparación paramétrica de Dc.
- Selección preliminar automática.
- Recomendaciones automáticas.
- Gráficas.
- Informe TXT y resultados CSV.
- Pantallas separadas para:
    1. Datos de entrada
    2. Resultados
    3. Geometría
    4. Análisis de partículas
    5. Comparación Dc
    6. Recomendaciones
    7. Informe

INSTALACIÓN
-----------
pip install numpy matplotlib pillow reportlab

Ejecutar:
python SYCSAtech_Calculador_Ciclones_v5.py

IMPORTANTE
----------
Es una herramienta de prediseño. Las correlaciones son aproximadas y
deben validarse con la geometría real, concentración de sólidos,
granulometría medida, condiciones de operación y/o pruebas.

REFERENCIA DE PROPIEDADES DE AIRE
---------------------------------
IAEA, Thermophysical Properties of Materials, Table 3.1,
Thermophysical properties of dry air at P = 0.0981 MPa.
La tabla se interpola en función de la temperatura.
"""

import csv
import math
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

import numpy as np
import matplotlib.pyplot as plt

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============================================================
# IDENTIDAD VISUAL
# ============================================================


# ============================================================================
# REFERENCIAS BIBLIOGRÁFICAS Y CRITERIO DE IMPLEMENTACIÓN — V11
# ============================================================================
#
# [R1] Stairmand, C. J. (1951). The design and performance of cyclone
#      separators. Transactions of the Institution of Chemical Engineers,
#      29, 356–383.
#      Base principal de las proporciones geométricas del ciclón Stairmand.
#
# [R2] Lapple, C. E. (1951). Processes use many collector types.
#      Chemical Engineering, 58, 144–151.
#      Base histórica del método de diámetro de corte usado en el programa.
#
# [R3] Shepherd, C. B., & Lapple, C. E. (1939). Flow pattern and pressure
#      drop in cyclone dust collectors. Industrial & Engineering Chemistry,
#      31(8), 972–984. https://doi.org/10.1021/ie50356a012
#      Base experimental para patrón de flujo y pérdida de presión.
#
# [R4] Leith, D., & Mehta, D. (1973). Cyclone performance and design.
#      Atmospheric Environment, 7(5), 527–549.
#      https://doi.org/10.1016/0004-6981(73)90006-1
#      Referencia para evaluación de modelos de presión/eficiencia y diseño.
#
# [R5] U.S. EPA. (1981). APTI Course 413: Control of Particulate Emissions.
#      Manual de formación sobre ciclones, método de Lapple y eficiencia.
#
# [R6] U.S. EPA. (2003). Air Pollution Control Technology Fact Sheet: Cyclones.
#      Relación entre tamaño de partícula, velocidad, eficiencia y presión.
#
# [R7] Hoffmann, A. C., & Stein, L. E. (2002). Gas cyclones and swirl tubes:
#      Principles, design, and operation. Springer.
#      https://doi.org/10.1007/978-3-662-07377-3
#      Fundamento moderno de flujo, presión, eficiencia y diseño.
#
# [R8] ASME BPVC Section VIII, Division 1.
#      Referencia normativa para recipientes bajo presión interna/externa.
#
# [R9] ASME BPVC Section II, Part D.
#      Propiedades y esfuerzos admisibles de materiales cuando corresponda.
#
# [R10] ASME B36.10/B36.10M. Dimensiones de tubería de acero al carbón.
# [R11] ASME B36.19/B36.19M. Dimensiones de tubería de acero inoxidable.
#
# IMPORTANTE:
#   Las ecuaciones del módulo de proceso son correlaciones/modelos de
#   prediseño. Las relaciones geométricas corresponden al tipo de ciclón
#   seleccionado. El módulo estructural es un SCREENING simplificado:
#   NO reproduce íntegramente ASME UG-28/UG-29 ni constituye certificación.
# ============================================================================


# ============================================================================
# TKINTER FONT SAFETY
# ============================================================================
# Tkinter/Tcl expects the point size in a font tuple to be an integer.
# This helper prevents a decimal such as 7.5 from reaching Tcl.
def tk_font(size=9, family="Segoe UI", weight=None):
    size = int(round(float(size)))
    if weight:
        return (family, size, weight)
    return (family, size)


NAVY = "#172957"
NAVY_DARK = "#0B1B40"
NAVY_LIGHT = "#20386E"
TEAL = "#00A99D"
TEAL_DARK = "#008F88"
TEAL_LIGHT = "#DDF5F3"
WHITE = "#FFFFFF"
BG = "#F3F6FA"
CARD = "#FFFFFF"
TEXT = "#17213A"
MUTED = "#61708D"
BORDER = "#D7DFEC"
GREEN = "#168A63"
ORANGE = "#E88A17"
RED = "#C94141"
PURPLE = "#7B4FB3"


# ============================================================
# DATOS
# ============================================================

MATERIALES = {
    "PET (Pellet)": {"rho": 1377.59, "dpg": 3175, "sigma": 1.15},
    "HDPE (Pellet)": {"rho": 950, "dpg": 3000, "sigma": 1.15},
    "PP (Pellet)": {"rho": 900, "dpg": 3000, "sigma": 1.15},
    "PVC (Polvo)": {"rho": 1400, "dpg": 100, "sigma": 2.00},
    "Harina": {"rho": 600, "dpg": 100, "sigma": 2.00},
    "Talco": {"rho": 2700, "dpg": 20, "sigma": 2.00},
    "Carbonato de calcio": {"rho": 2710, "dpg": 25, "sigma": 1.80},
    "Cemento": {"rho": 3150, "dpg": 30, "sigma": 1.80},
    "Personalizado": {"rho": 1000, "dpg": 100, "sigma": 2.00},
}

FLOW = {
    "m³/s": 1.0,
    "m³/min": 1 / 60,
    "m³/h": 1 / 3600,
    "L/s": 0.001,
    "L/min": 0.001 / 60,
    "L/h": 0.001 / 3600,
    "CFM": 0.00047194745,
}

LENGTH = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "µm": 1e-6,
    "in": 0.0254,
    "ft": 0.3048,
}

PRESSURE = {
    "Pa": 1.0,
    "kPa": 1000.0,
    "bar": 100000.0,
    "mbar": 100.0,
    "psi": 6894.757,
    "inH₂O": 249.0889,
    "inHg": 3386.389,
}


# Tabla de propiedades de aire seco usada por el programa.
# Fuente bibliográfica: IAEA, Thermophysical Properties of Materials,
# Table 3.1, Dry air at P = 0.0981 MPa.
# Los valores se interpolan linealmente para la temperatura introducida.
# La densidad se corrige posteriormente a la presión absoluta indicada.
AIR_TABLE = np.array([
    [-50.0, 1.532, 13.40e-6],
    [-20.0, 1.350, 16.80e-6],
    [0.0,   1.251, 17.19e-6],
    [10.0,  1.207, 17.69e-6],
    [20.0,  1.166, 18.19e-6],
    [30.0,  1.127, 18.68e-6],
    [40.0,  1.091, 19.16e-6],
    [50.0,  1.057, 19.63e-6],
    [60.0,  1.026, 20.10e-6],
    [70.0,  0.996, 20.56e-6],
    [80.0,  0.967, 21.02e-6],
    [90.0,  0.941, 21.47e-6],
    [100.0, 0.916, 21.99e-6],
], dtype=float)

AIR_TABLE_PRESSURE = 0.0981e6  # Pa


def convert(value, unit, table):
    return float(value) * table[unit]


def air_properties(T_K, P_abs):
    """Obtiene propiedades de aire seco a partir de la temperatura.

    La viscosidad dinámica se obtiene por interpolación de la tabla IAEA
    de aire seco. La densidad se obtiene de la misma tabla y se corrige
    proporcionalmente por la presión absoluta de operación.

    Rango recomendado de la tabla: -50 a 100 °C.
    """
    T_C = T_K - 273.15

    if T_C < AIR_TABLE[0, 0] or T_C > AIR_TABLE[-1, 0]:
        raise ValueError(
            "La tabla de propiedades de aire está disponible entre "
            "-50 y 100 °C. Para temperaturas fuera de este rango se "
            "requiere una correlación de mayor rango o una fuente de "
            "propiedades específica."
        )

    rho_table = float(np.interp(T_C, AIR_TABLE[:, 0], AIR_TABLE[:, 1]))
    mu = float(np.interp(T_C, AIR_TABLE[:, 0], AIR_TABLE[:, 2]))

    # Para gas diluido, μ depende principalmente de T; ρ se corrige con P/T.
    rho = rho_table * (P_abs / AIR_TABLE_PRESSURE)

    return rho, mu


# ============================================================
# MODELOS
# ============================================================

@dataclass
class Geometry:
    name: str
    a: float
    b: float
    De: float
    S: float
    h: float
    H: float
    B: float


@dataclass
class Result:
    Dc: float
    geometry: Geometry
    Q_cyclone: float
    area_inlet: float
    V_in: float
    V_can: float
    Reynolds: float
    dpc: float
    eta_global: float
    eta_curve: np.ndarray
    deltaP: float
    residence_time: float
    n_cyclones: int


# TEORÍA — GEOMETRÍA
# Las relaciones geométricas normalizadas expresan cada dimensión como una
# fracción de Dc. Stairmand (1951) establece familias geométricamente semejantes.
def cyclone_geometry(Dc, cyclone_type):
    if cyclone_type == "Stairmand (EPA)":
        ratios = (0.50, 0.20, 0.50, 0.50, 1.50, 4.00, 0.375)
    else:
        ratios = (0.50, 0.25, 0.50, 0.625, 2.00, 4.00, 0.25)

    values = [x * Dc for x in ratios]
    return Geometry(cyclone_type, *values)


# TEORÍA — DISTRIBUCIÓN LOG-NORMAL
# ln(dp) se modela como aproximadamente normal. Los pesos se normalizan para
# que sumen 1. Es una aproximación de prediseño cuando no existe PSD medida.
def lognormal_psd(dpg_um, sigma_g, n=140):
    if dpg_um <= 0:
        raise ValueError("El diámetro medio debe ser mayor que cero.")
    if sigma_g <= 1:
        raise ValueError("σg debe ser mayor que 1.")

    low = max(dpg_um / 20, 0.01)
    high = dpg_um * 20

    dp_um = np.logspace(
        math.log10(low),
        math.log10(high),
        n,
    )

    s = math.log(sigma_g)
    x = np.log(dp_um / dpg_um)

    pdf = np.exp(-0.5 * (x / s) ** 2) / (
        dp_um * s * math.sqrt(2 * math.pi)
    )

    weights = pdf / np.sum(pdf)
    return dp_um * 1e-6, weights


# TEORÍA — DIÁMETRO DE CORTE (LAPPLE)
# El modelo relaciona arrastre, migración centrífuga y propiedades de la
# partícula. EPA/APTI presenta la forma usada para prediseño.
def cut_diameter(mu, b, rho_particle, V_in, Ne):
    return math.sqrt(
        9 * mu * b
        /
        (
            2 * math.pi * Ne * rho_particle * V_in
        )
    )


# TEORÍA — EFICIENCIA FRACCIONAL
# eta=1/[1+(dpc/dp)^2] es una correlación de prediseño con eta(dpc)=0.5.
def fractional_efficiency(dp, dpc):
    dp = np.asarray(dp, dtype=float)
    return 1.0 / (1.0 + (dpc / dp) ** 2)


# TEORÍA — EFICIENCIA GLOBAL
# eta_global=sum(eta_i*w_i), ponderando por la distribución granulométrica.
def global_efficiency(dp, weights, dpc):
    return float(
        np.sum(fractional_efficiency(dp, dpc) * weights)
    )


# TEORÍA — PÉRDIDA DE PRESIÓN
# DeltaP=K*rho*Vi^2/2: K agrupa las pérdidas como múltiplo de presión dinámica.
def pressure_drop(rho_air, V_in, K):
    return K * rho_air * V_in ** 2 / 2


# TEORÍA — BALANCES BÁSICOS
# Qc=Q/N, Ae=a*b, Vi=Qc/Ae, Ac=pi*Dc²/4, Vcan=Qc/Ac, Re=rho*Vi*Dc/mu.
# Estas relaciones proceden de continuidad, geometría y definición de Reynolds.
def calculate(
    Q_total,
    T_K,
    P_abs,
    rho_air,
    mu_air,
    rho_particle,
    Dc,
    n_cyclones,
    cyclone_type,
    psd_dp,
    psd_weights,
    Ne,
    K,
):
    if Q_total <= 0 or Dc <= 0:
        raise ValueError("Caudal y Dc deben ser mayores que cero.")
    if n_cyclones < 1:
        raise ValueError("El número de ciclones debe ser al menos 1.")
    if rho_particle <= 0:
        raise ValueError("La densidad de partícula debe ser positiva.")
    if Ne <= 0 or K <= 0:
        raise ValueError("Ne y K deben ser mayores que cero.")

    geo = cyclone_geometry(Dc, cyclone_type)
    Qc = Q_total / n_cyclones
    A_in = geo.a * geo.b
    V_in = Qc / A_in
    A_cyl = math.pi * Dc ** 2 / 4
    V_can = Qc / A_cyl
    Re = rho_air * V_in * Dc / mu_air

    dpc = cut_diameter(
        mu_air,
        geo.b,
        rho_particle,
        V_in,
        Ne,
    )

    eta_curve = fractional_efficiency(psd_dp, dpc)
    eta_global = global_efficiency(psd_dp, psd_weights, dpc)
    deltaP = pressure_drop(rho_air, V_in, K)
    residence_time = Ne * math.pi * Dc / V_in

    return Result(
        Dc,
        geo,
        Qc,
        A_in,
        V_in,
        V_can,
        Re,
        dpc,
        eta_global,
        eta_curve,
        deltaP,
        residence_time,
        n_cyclones,
    )


# ============================================================
# PREDISEÑO ESTRUCTURAL — SCREENING
# ============================================================

STRUCTURAL_MATERIALS = {
    "Acero al carbón": {
        "E_GPa": 200.0,
        "nu": 0.30,
        "Sy_MPa": 250.0,
    },
    "Acero inoxidable 304": {
        "E_GPa": 193.0,
        "nu": 0.29,
        "Sy_MPa": 215.0,
    },
    "Acero inoxidable 316": {
        "E_GPa": 193.0,
        "nu": 0.30,
        "Sy_MPa": 205.0,
    },
    "Aluminio 5052": {
        "E_GPa": 70.3,
        "nu": 0.33,
        "Sy_MPa": 193.0,
    },
    "Aluminio 6061": {
        "E_GPa": 68.9,
        "nu": 0.33,
        "Sy_MPa": 276.0,
    },
}

COMMERCIAL_SHEET_MM = [
    1.5, 2.0, 2.5, 3.0, 4.0, 5.0,
    6.0, 8.0, 10.0, 12.0, 16.0,
]

def _screening_internal_shell_thickness(P, D, S_allow, weld_eff):
    """
    Espesor preliminar por presión interna mediante equilibrio de esfuerzos
    de membrana para una envolvente cilíndrica.

    Base teórica: equilibrio de esfuerzos de pared delgada y conceptos de
    recipientes a presión tratados en ASME BPVC VIII-1 [R4].

    Este cálculo se usa únicamente como SCREENING. No sustituye la ecuación,
    material, eficiencia de junta, temperatura y demás requisitos normativos
    que correspondan al diseño final.
    """
    if P <= 0:
        return 0.0
    denom = 2.0 * S_allow * weld_eff - P
    if denom <= 0:
        return float("inf")
    return P * D / denom


def _external_buckling_pressure(D, L, t, E, nu, rings=0,
                                knockdown=0.20):
    """
    Screening de pandeo elástico de una envolvente cilíndrica.

    Base teórica: teoría de pandeo elástico de cascarones cilíndricos y
    concepto de presión externa de ASME BPVC VIII-1 [R4].

    La función usa una relación elástica simplificada, un factor de reducción
    por imperfecciones y una aproximación del efecto de anillos mediante la
    reducción de la longitud libre. NO implementa literalmente las gráficas
    ni el procedimiento normativo UG-28/UG-29; por ello el resultado es
    solamente un prediseño.
    """
    if D <= 0 or L <= 0 or t <= 0:
        return 0.0

    L_eff = L / (rings + 1.0)

    p_el = (
        2.0 * E
        / math.sqrt(3.0 * (1.0 - nu ** 2))
        * (t / D) ** 3
    )

    finite_length_factor = math.sqrt(
        1.0 + (D / L_eff) ** 2
    )

    return p_el * knockdown * finite_length_factor


def _flat_head_bending_screen(P, D, S_allow, FS, nu):
    """
    Screening de una tapa plana circular por flexión.

    Base teórica: teoría clásica de placas circulares sometidas a presión.
    Se utiliza solamente para comparar una tapa plana frente a una tapa
    formada. El diseño definitivo de un cabezal debe seguir el código
    aplicable, incluyendo geometría, apoyos, soldaduras, aberturas y presión
    externa [R4].
    """
    if P <= 0:
        return 0.0

    a = D / 2.0
    if S_allow <= 0:
        return float("inf")

    # Relación simplificada de esfuerzo de flexión para una placa
    # circular. Se usa como screening, no como diseño de cabezal ASME.
    return a * math.sqrt(
        (3.0 + nu) * P * FS
        / (8.0 * S_allow)
    )


def _next_commercial_thickness(required_mm):
    for t in COMMERCIAL_SHEET_MM:
        if t >= required_mm:
            return t
    return COMMERCIAL_SHEET_MM[-1]


def structural_screening(
    result,
    data,
    corrosion_mm=1.0,
    weld_eff=0.85,
    FS=2.0,
    max_rings=4,
):
    """
    Prediseño estructural preliminar del cuerpo y cono del ciclón.

    Evalúa:
      - presión interna por membrana;
      - presión externa por pandeo elástico simplificado;
      - efecto aproximado de anillos rigidizadores;
      - tapa plana por flexión como referencia;
      - selección de espesor comercial.

    El resultado es deliberadamente denominado SCREENING.
    """
    if FS <= 1.0:
        raise ValueError("El factor de seguridad debe ser mayor que 1.")
    if not 0.50 <= weld_eff <= 1.0:
        raise ValueError("La eficiencia de soldadura debe estar entre 0.50 y 1.00.")
    if corrosion_mm < 0:
        raise ValueError("La sobre-espesor por corrosión no puede ser negativo.")
    if max_rings < 0 or int(max_rings) != max_rings:
        raise ValueError("El número máximo de anillos debe ser un entero >= 0.")

    mat_name = data["construction_material"]
    mat = STRUCTURAL_MATERIALS[mat_name]

    # Propiedades mecánicas en SI.
    # Para un diseño normativo real, E, Sy y los esfuerzos admisibles deben
    # seleccionarse de la especificación/temperatura/condición del material
    # aplicable, con ASME Section II-D [R5] cuando corresponda.
    E = mat["E_GPa"] * 1e9
    nu = mat["nu"]
    Sy = mat["Sy_MPa"] * 1e6

    # Criterio interno de screening; NO es un esfuerzo permisible ASME.
    S_allow = 0.40 * Sy

    P_internal = max(
        float(data["design_pressure_gauge_pa"]),
        0.0,
    )
    P_external = max(
        -float(data["design_pressure_gauge_pa"]),
        0.0,
    )

    D = result.Dc
    Hcyl = result.geometry.h
    cone_height = max(
        result.geometry.H - result.geometry.h,
        1e-9,
    )

    cone_slant = math.sqrt(
        cone_height ** 2
        + ((result.Dc - result.geometry.B) / 2.0) ** 2
    )

    D_cone = (
        result.Dc
        + result.geometry.B
    ) / 2.0

    # La presión interna se revisa mediante esfuerzos de membrana.
    # En ciclones que operan en vacío, la presión externa suele ser la
    # condición mecánica más importante y puede gobernar por pandeo.
    t_int_cyl = _screening_internal_shell_thickness(
        P_internal,
        D,
        S_allow,
        weld_eff,
    )

    t_int_cone = _screening_internal_shell_thickness(
        P_internal,
        D_cone,
        S_allow,
        weld_eff,
    )

    # Búsqueda paramétrica de espesor comercial + anillos.
    # Se exige P_admisible >= P_externa_de_diseño. La lógica de comparar
    # presión admisible contra presión externa es coherente con el enfoque
    # de verificación de presión externa de ASME VIII-1 [R4], aunque la
    # ecuación de pandeo usada aquí es simplificada y no es UG-28.
    candidates = []

    for rings in range(int(max_rings) + 1):
        for nominal_mm in COMMERCIAL_SHEET_MM:
            net_mm = nominal_mm - corrosion_mm

            if net_mm <= 0:
                continue

            t = net_mm / 1000.0

            p_allow_cyl = (
                _external_buckling_pressure(
                    D,
                    Hcyl,
                    t,
                    E,
                    nu,
                    rings=rings,
                )
                / FS
            )

            p_allow_cone = (
                _external_buckling_pressure(
                    D_cone,
                    cone_slant,
                    t,
                    E,
                    nu,
                    rings=0,
                )
                / FS
            )

            p_allow = min(
                p_allow_cyl,
                p_allow_cone,
            )

            candidates.append({
                "rings": rings,
                "nominal_mm": nominal_mm,
                "net_mm": net_mm,
                "p_allow_cyl": p_allow_cyl,
                "p_allow_cone": p_allow_cone,
                "p_allow": p_allow,
            })

    valid = [
        c for c in candidates
        if c["p_allow"] >= P_external
        and c["net_mm"] / 1000.0 >= max(
            t_int_cyl,
            t_int_cone,
        )
    ]

    if valid:
        # Prefer smaller sheet; if equal, fewer rings.
        selected = min(
            valid,
            key=lambda c: (
                c["nominal_mm"],
                c["rings"],
            ),
        )
    else:
        # If no combination works, report the largest tested option.
        selected = max(
            candidates,
            key=lambda c: (
                c["p_allow"],
                c["nominal_mm"],
                -c["rings"],
            ),
        )

    nominal = selected["nominal_mm"]
    net = selected["net_mm"]
    rings = selected["rings"]

    p_allow_structural = selected["p_allow"]

    # Head screening.
    flat_head_net = _flat_head_bending_screen(
        P_external,
        D,
        S_allow,
        FS,
        nu,
    )

    flat_head_nominal = _next_commercial_thickness(
        flat_head_net * 1000.0 + corrosion_mm
    )

    if P_external <= 5000:
        head_recommendation = (
            "Tapa plana reforzada puede ser evaluada; "
            "verificar rigidez y pandeo."
        )
    elif P_external <= 30000:
        head_recommendation = (
            "Se recomienda tapa formada, preferentemente "
            "toriesférica o elíptica 2:1, con verificación de "
            "presión externa."
        )
    else:
        head_recommendation = (
            "Se recomienda tapa formada y cálculo específico "
            "de presión externa; no usar tapa plana sin "
            "verificación estructural."
        )

    if P_external > 0:
        head_status = "Tapa formada recomendada" if P_external > 5000 else "Revisión de tapa plana"
    else:
        head_status = "Tapa según presión interna y fabricación"

    utilization = (
        P_external / p_allow_structural
        if p_allow_structural > 0
        else float("inf")
    )

    shell_required_net = max(
        t_int_cyl,
        t_int_cone,
    ) * 1000.0

    # El espesor nominal debe contener el sobreespesor de corrosión.
    required_nominal = shell_required_net + corrosion_mm
    required_nominal = max(
        required_nominal,
        0.0,
    )

    # Revisión separada de la solución seleccionada.
    p_cyl_selected = selected["p_allow_cyl"]
    p_cone_selected = selected["p_allow_cone"]

    status = (
        "CUMPLE SCREENING"
        if (
            P_external <= p_allow_structural
            and nominal - corrosion_mm >= shell_required_net
        )
        else "NO CUMPLE SCREENING"
    )

    # Recomendación de anillos.
    if P_external <= 0:
        ring_note = "No se requieren anillos por vacío; revisar cargas externas."
    elif rings == 0:
        ring_note = "No se requieren anillos en este screening; verificar pandeo detallado."
    elif rings == 1:
        ring_note = "1 anillo rigidizador recomendado como prediseño."
    else:
        ring_note = (
            f"{rings} anillos rigidizadores circunferenciales "
            "recomendados como prediseño."
        )

    return {
        "material": mat_name,
        "E_GPa": mat["E_GPa"],
        "nu": nu,
        "Sy_MPa": mat["Sy_MPa"],
        "S_allow_MPa": S_allow / 1e6,
        "corrosion_mm": corrosion_mm,
        "weld_eff": weld_eff,
        "FS": FS,
        "P_internal_kPa": P_internal / 1000.0,
        "P_external_kPa": P_external / 1000.0,
        "shell_t_internal_mm": t_int_cyl * 1000.0,
        "cone_t_internal_mm": t_int_cone * 1000.0,
        "required_nominal_mm": required_nominal,
        "selected_nominal_mm": nominal,
        "selected_net_mm": net,
        "rings": rings,
        "p_allow_cyl_kPa": p_cyl_selected / 1000.0,
        "p_allow_cone_kPa": p_cone_selected / 1000.0,
        "p_allow_structural_kPa": p_allow_structural / 1000.0,
        "utilization": utilization,
        "flat_head_net_mm": flat_head_net * 1000.0,
        "flat_head_nominal_mm": flat_head_nominal,
        "head_recommendation": head_recommendation,
        "head_status": head_status,
        "ring_note": ring_note,
        "status": status,
        "screening_note": (
            "Prediseño estructural preliminar. No constituye una "
            "verificación de cumplimiento ASME. El pandeo por presión "
            "externa depende de geometría, ovalidad, longitud libre, "
            "soldaduras, rigidizadores, tolerancias y condiciones de "
            "fabricación."
        ),
    }


# ============================================================
# ENTRADA CIRCULAR — RECOMENDACIÓN DE PREDISEÑO
# ============================================================

def inlet_pipe_recommendation(result):
    """
    Calcula el diámetro interno equivalente de una entrada circular que
    conserve, como primera aproximación, el área de la entrada tangencial
    rectangular del ciclón.

    Base:
        Ae = a*b
        Deq = sqrt(4*Ae/pi)
        Vi = Qc/Ae

    La recomendación no convierte automáticamente la geometría Stairmand en
    una entrada circular normativamente equivalente. La transición circular
    -> tangencial debe diseñarse para evitar contracciones bruscas, separación
    de flujo y pérdidas adicionales.

    Para la especificación de tubería se recomienda consultar dimensiones
    comerciales de ASME B36.10/B36.10M para acero al carbón y ASME B36.19/B36.19M
    para acero inoxidable, seleccionando un diámetro interior real igual o
    ligeramente mayor que Deq y verificando la velocidad resultante.
    """
    g = result.geometry
    area_rect = max(g.a * g.b, 1e-12)
    deq = math.sqrt(4.0 * area_rect / math.pi)
    q = result.Q_cyclone
    v_eq = q / area_rect

    return {
        "area_rect_m2": area_rect,
        "deq_m": deq,
        "velocity_m_s": v_eq,
        "recommendation": (
            "Entrada circular mediante tubería comercial calibrada o "
            "Schedule 10/10S, conectada a una transición circular-tangencial. "
            "Seleccionar un diámetro interior comercial igual o ligeramente "
            "mayor que el diámetro equivalente y verificar la velocidad."
        ),
        "standards_note": (
            "Dimensiones de tubería: ASME B36.10/B36.10M para acero al carbón "
            "y ASME B36.19/B36.19M para acero inoxidable."
        ),
    }



# ============================================================
# BIBLIOTECA DE TUBERÍAS COMERCIALES
# ============================================================
#
# Valores nominales para selección preliminar de diámetro.
# Fuente dimensional:
#   [R8] ASME B36.10/B36.10M — Welded and Seamless Wrought Steel Pipe.
#   [R9] ASME B36.19/B36.19M — Stainless Steel Pipe.
#
# OD y espesores son valores nominales; el ID se calcula como:
#       ID = OD - 2*t
#
# La selección de una tubería por diámetro NO constituye una verificación
# de presión, vacío, flexión, soporte, vibración ni conexión.
#
PIPE_LIBRARY = {
    "Acero al carbón": {
        "standard": "ASME B36.10/B36.10M",
        "schedules": {
            "10": {
                "2": (60.3, 2.77),
                "2.5": (73.0, 3.05),
                "3": (88.9, 3.05),
                "4": (114.3, 3.05),
                "5": (141.3, 3.40),
                "6": (168.3, 3.40),
                "8": (219.1, 3.76),
                "10": (273.1, 4.19),
                "12": (323.8, 4.57),
            },
            "40": {
                "2": (60.3, 3.91),
                "2.5": (73.0, 5.16),
                "3": (88.9, 5.49),
                "4": (114.3, 6.02),
                "5": (141.3, 6.55),
                "6": (168.3, 7.11),
                "8": (219.1, 8.18),
                "10": (273.1, 9.27),
                "12": (323.8, 10.31),
            },
        },
    },
    "Acero inoxidable 304": {
        "standard": "ASME B36.19/B36.19M",
        "schedules": {
            "10S": {
                "2": (60.3, 2.77),
                "2.5": (73.0, 3.05),
                "3": (88.9, 3.05),
                "4": (114.3, 3.05),
                "5": (141.3, 3.40),
                "6": (168.3, 3.40),
                "8": (219.1, 3.76),
                "10": (273.0, 4.19),
                "12": (323.8, 4.57),
            },
            "40S": {
                "2": (60.3, 3.91),
                "2.5": (73.0, 5.16),
                "3": (88.9, 5.49),
                "4": (114.3, 6.02),
                "5": (141.3, 6.55),
                "6": (168.3, 7.11),
                "8": (219.1, 8.18),
                "10": (273.0, 9.27),
                "12": (323.8, 9.52),
            },
        },
    },
    "Acero inoxidable 316": {
        "standard": "ASME B36.19/B36.19M",
        "schedules": {
            "10S": {
                "2": (60.3, 2.77),
                "2.5": (73.0, 3.05),
                "3": (88.9, 3.05),
                "4": (114.3, 3.05),
                "5": (141.3, 3.40),
                "6": (168.3, 3.40),
                "8": (219.1, 3.76),
                "10": (273.0, 4.19),
                "12": (323.8, 4.57),
            },
            "40S": {
                "2": (60.3, 3.91),
                "2.5": (73.0, 5.16),
                "3": (88.9, 5.49),
                "4": (114.3, 6.02),
                "5": (141.3, 6.55),
                "6": (168.3, 7.11),
                "8": (219.1, 8.18),
                "10": (273.0, 9.27),
                "12": (323.8, 9.52),
            },
        },
    },
}


def pipe_candidates(result, construction_material, vmin=12.0, vmax=25.0):
    """
    Compara tuberías comerciales mediante dos criterios independientes:

    A) Área equivalente:
       ID >= Deq, para conservar aproximadamente el área de la entrada
       rectangular Stairmand.

    B) Velocidad objetivo:
       Vmin <= Q/A_pipe <= Vmax.

    Si la geometría del ciclón ya cumple el rango de velocidad, se recomienda
    el menor diámetro comercial que conserve el área equivalente.

    Si la geometría NO cumple el rango de velocidad, el programa NO "corrige"
    el problema aumentando el diámetro de la tubería. En su lugar muestra el
    diámetro comercial que podría producir la velocidad objetivo y marca
    que debe revisarse la geometría del ciclón.

    Esto evita recomendar una tubería mayor cuando la velocidad ya es baja.
    """
    rec = inlet_pipe_recommendation(result)
    deq = rec["deq_m"]
    q = result.Q_cyclone
    v_eq = rec["velocity_m_s"]

    if construction_material not in PIPE_LIBRARY:
        return {
            "available": False,
            "standard": "No aplica a esta biblioteca",
            "deq_m": deq,
            "velocity_equivalent_m_s": v_eq,
            "candidates": [],
            "selected": None,
            "area_match": None,
            "velocity_match": None,
            "velocity_conflict": True,
            "status": "REVISAR",
            "selection_basis": "Biblioteca no disponible para este material.",
            "conflict_message": (
                "Para aluminio se requiere seleccionar tubo comercial por "
                "diámetro interior y espesor del fabricante."
            ),
            "message": (
                "Para aluminio no se aplica automáticamente la biblioteca "
                "ASME B36.10/B36.19."
            ),
        }

    lib = PIPE_LIBRARY[construction_material]
    candidates = []

    for schedule, sizes in lib["schedules"].items():
        for nps, (od_mm, wall_mm) in sizes.items():
            id_mm = od_mm - 2.0 * wall_mm
            id_m = id_mm / 1000.0
            area = math.pi * id_m**2 / 4.0
            velocity = q / max(area, 1e-12)

            candidates.append({
                "schedule": schedule,
                "nps": nps,
                "dn": nps_to_dn(nps),
                "od_mm": od_mm,
                "wall_mm": wall_mm,
                "id_mm": id_mm,
                "area_m2": area,
                "velocity_m_s": velocity,
                "area_ok": id_m >= deq,
                "velocity_ok": vmin <= velocity <= vmax,
                "recommended": False,
            })

    area_candidates = [c for c in candidates if c["area_ok"]]
    velocity_candidates = [c for c in candidates if c["velocity_ok"]]

    area_match = (
        min(area_candidates, key=lambda c: c["id_mm"])
        if area_candidates else None
    )
    velocity_match = (
        min(velocity_candidates, key=lambda c: c["id_mm"])
        if velocity_candidates else None
    )

    velocity_conflict = not (vmin <= v_eq <= vmax)

    if not velocity_conflict and area_match:
        selected = area_match
        selected["recommended"] = True
        status = "CUMPLE"
        selection_basis = (
            "La geometría cumple Vmin–Vmax; se selecciona el menor "
            "ID comercial que conserva aproximadamente el área de entrada."
        )
    elif velocity_match:
        selected = velocity_match
        selected["recommended"] = True
        status = "REQUIERE REDISEÑO"
        selection_basis = (
            "La geometría actual no cumple Vmin–Vmax. Este diámetro muestra "
            "una alternativa comercial para alcanzar la velocidad objetivo, "
            "pero requiere revisar la geometría de entrada."
        )
    else:
        selected = area_match
        if selected:
            selected["recommended"] = True
        status = "REVISAR"
        selection_basis = (
            "No existe una alternativa de la biblioteca que cumpla "
            "simultáneamente el rango de velocidad configurado."
        )

    if velocity_conflict:
        if v_eq < vmin:
            conflict_message = (
                f"V geométrica={v_eq:.2f} m/s < Vmin={vmin:.2f} m/s. "
                "Aumentar el diámetro de tubería reduciría todavía más la "
                "velocidad; revise Dc, número de ciclones o dimensiones de entrada."
            )
        else:
            conflict_message = (
                f"V geométrica={v_eq:.2f} m/s > Vmax={vmax:.2f} m/s. "
                "Revise la geometría/caudal antes de definir la conexión."
            )
    else:
        conflict_message = (
            f"V geométrica={v_eq:.2f} m/s está dentro de Vmin–Vmax."
        )

    return {
        "available": True,
        "standard": lib["standard"],
        "deq_m": deq,
        "velocity_equivalent_m_s": v_eq,
        "candidates": sorted(
            candidates,
            key=lambda c: (float(c["nps"].replace("-", ".")), c["schedule"])
        ),
        "selected": selected,
        "area_match": area_match,
        "velocity_match": velocity_match,
        "velocity_conflict": velocity_conflict,
        "status": status,
        "selection_basis": selection_basis,
        "conflict_message": conflict_message,
        "message": (
            f"Área equivalente: "
            f"{('NPS ' + area_match['nps'] + ' Sch ' + area_match['schedule']) if area_match else 'sin candidato'}; "
            f"velocidad objetivo: "
            f"{('NPS ' + velocity_match['nps'] + ' Sch ' + velocity_match['schedule']) if velocity_match else 'sin candidato'}."
        ),
    }


def nps_to_dn(nps):
    """Equivalencia DN nominal para los tamaños incluidos."""
    mapping = {
        "2": 50,
        "2.5": 65,
        "3": 80,
        "4": 100,
        "5": 125,
        "6": 150,
        "8": 200,
        "10": 250,
        "12": 300,
    }
    return mapping.get(nps, "—")


# ============================================================
# RECOMENDACIONES
# ============================================================

CONSTRUCTION_GUIDANCE = {
    "Acero al carbón": {
        "practical_min_mm": 3.0,
        "light_mm": 3.0,
        "vacuum_mm": 4.5,
        "head": "Tapa formada (torisférica o elíptica) preferible para vacío significativo.",
        "note": "Buena opción económica; requiere protección anticorrosiva y verificación de desgaste."
    },
    "Acero inoxidable 304": {
        "practical_min_mm": 2.5,
        "light_mm": 2.5,
        "vacuum_mm": 4.0,
        "head": "Tapa formada preferible cuando el vacío sea significativo o exista riesgo de colapso de una tapa plana.",
        "note": "Adecuado para ambientes donde se requiere resistencia a corrosión y limpieza."
    },
    "Acero inoxidable 316": {
        "practical_min_mm": 2.5,
        "light_mm": 2.5,
        "vacuum_mm": 4.0,
        "head": "Tapa formada preferible para vacío significativo.",
        "note": "Preferible frente a 304 cuando el ambiente o material procesado justifique mayor resistencia a corrosión."
    },
    "Aluminio 5052": {
        "practical_min_mm": 3.0,
        "light_mm": 3.0,
        "vacuum_mm": 5.0,
        "head": "Para vacío importante, usar tapa formada y/o rigidización calculada.",
        "note": "Ligero, pero su menor módulo elástico hace especialmente importante revisar pandeo por presión externa."
    },
    "Aluminio 6061": {
        "practical_min_mm": 3.0,
        "light_mm": 3.0,
        "vacuum_mm": 5.0,
        "head": "Para vacío importante, usar tapa formada y/o rigidización calculada.",
        "note": "Buena relación resistencia/peso; revisar condición de temple, soldadura y propiedades permisibles."
    },
}


def mechanical_design_recommendation(
    construction_material,
    pressure_mode,
    design_pressure_gauge_pa,
    Dc,
):
    """
    Recomendación preliminar de material/espesor.

    IMPORTANTE:
    No es un cálculo de espesor según ASME. Para presión externa/vacío,
    el modo de falla puede ser pandeo y depende de geometría, ovalidad,
    rigidizadores, longitud no soportada, soldaduras y condiciones de
    fabricación. El resultado se presenta deliberadamente como
    'espesor preliminar de especificación', no como espesor calculado.
    """
    info = CONSTRUCTION_GUIDANCE[construction_material]

    if pressure_mode == "Vacío":
        vacuum_kpa = max(abs(design_pressure_gauge_pa) / 1000.0, 0.0)

        if vacuum_kpa < 5:
            severity = "Vacío ligero"
            thickness = info["light_mm"]
            head = "Tapa plana reforzada puede ser viable, pero debe verificarse por pandeo."
            ring = "Rigidizadores: recomendables si la tapa o carcasa tiene gran diámetro."
        elif vacuum_kpa < 30:
            severity = "Vacío moderado"
            thickness = info["vacuum_mm"]
            head = "Se recomienda tapa formada (torisférica o elíptica) y verificación de pandeo."
            ring = "Rigidizadores circunferenciales: probablemente necesarios según longitud libre y espesor."
        else:
            severity = "Vacío alto"
            thickness = max(info["vacuum_mm"], info["practical_min_mm"] + 1.5)
            head = "Tapa formada y diseño específico para presión externa; no se recomienda una tapa plana sin cálculo."
            ring = "Rigidización y cálculo formal de presión externa/pandeo obligatorios."
    else:
        pressure_kpa = max(design_pressure_gauge_pa / 1000.0, 0.0)

        if pressure_kpa < 50:
            severity = "Presión baja"
            thickness = info["practical_min_mm"]
            head = "Tapa plana puede ser viable para baja presión, sujeto a cálculo."
            ring = "Rigidizadores según diámetro, abertura y cargas."
        elif pressure_kpa < 100:
            severity = "Presión moderada"
            thickness = info["practical_min_mm"] + 1.0
            head = "Tapa formada preferible; verificar código de recipiente a presión."
            ring = "Revisar rigidización y aberturas."
        else:
            severity = "Presión elevada"
            thickness = info["practical_min_mm"] + 2.0
            head = "Usar tapa formada diseñada bajo código de recipientes a presión."
            ring = "Diseño formal de carcasa, cabezal, rigidizadores y conexiones."

    return {
        "material": construction_material,
        "severity": severity,
        "pressure_kpa": abs(design_pressure_gauge_pa) / 1000.0,
        "recommended_sheet_mm": thickness,
        "head_recommendation": head,
        "stiffener_recommendation": ring,
        "material_note": info["note"],
        "caution": (
            "Valor preliminar para selección de concepto. No sustituye el "
            "cálculo de espesor y pandeo conforme al código aplicable."
        ),
    }


def recommendations(result, material, dpg_um, sigma, vmin, vmax,
                     eta_target, dp_max):
    items = []

    if result.V_in < vmin:
        items.append(("warning", "Velocidad de entrada baja",
                      f"{result.V_in:.1f} m/s está por debajo de {vmin:.1f} m/s. "
                      "Evalúe reducir Dc o revisar el reparto del caudal."))
    elif result.V_in > vmax:
        items.append(("danger", "Velocidad de entrada alta",
                      f"{result.V_in:.1f} m/s supera {vmax:.1f} m/s. "
                      "Puede aumentar desgaste, ΔP y re-entrainment."))
    else:
        items.append(("success", "Velocidad de entrada adecuada",
                      f"{result.V_in:.1f} m/s está dentro de "
                      f"{vmin:.1f}–{vmax:.1f} m/s."))

    eta = result.eta_global * 100
    if eta < eta_target:
        items.append(("danger", "Eficiencia inferior al objetivo",
                      f"{eta:.1f}% es menor que el objetivo de "
                      f"{eta_target:.1f}%. Considere reducir Dc, "
                      "aumentar ciclones en paralelo o cambiar geometría."))
    elif eta < 95:
        items.append(("warning", "Eficiencia aceptable pero mejorable",
                      f"La eficiencia estimada es {eta:.1f}%. "
                      "Para alta recuperación de finos evalúe filtración posterior."))
    else:
        items.append(("success", "Eficiencia alta",
                      f"La eficiencia global estimada es {eta:.1f}%."))

    dpc_um = result.dpc * 1e6
    if dpg_um <= dpc_um:
        items.append(("warning", "Partícula cercana al diámetro de corte",
                      f"dpg={dpg_um:.1f} µm y dpc={dpc_um:.1f} µm. "
                      "La fracción fina tendrá menor probabilidad de captura."))

    if dpg_um < 100:
        items.append(("warning", "Material fino",
                      f"{material} tiene un dpg de {dpg_um:.1f} µm. "
                      "Considere una etapa posterior de filtración si se "
                      "requiere alta captura de finos."))

    if sigma >= 2:
        items.append(("info", "Distribución granulométrica amplia",
                      f"σg={sigma:.2f}. Para diseño final se recomienda usar "
                      "una PSD medida del material real."))

    if result.deltaP > dp_max:
        items.append(("danger", "Pérdida de presión elevada",
                      f"ΔP≈{result.deltaP:.0f} Pa supera el límite "
                      f"de {dp_max:.0f} Pa."))
    else:
        items.append(("success", "Pérdida de presión dentro del límite",
                      f"ΔP≈{result.deltaP:.0f} Pa."))

    items.append(("tip", "Recomendación de ingeniería",
                  "No seleccione el ciclón únicamente por eficiencia. "
                  "Busque el equilibrio entre eficiencia, velocidad, ΔP, "
                  "desgaste y granulometría."))

    return items


def select_best(results, vmin, vmax, eta_target, dp_max):
    valid = [
        r for r in results
        if vmin <= r.V_in <= vmax
        and r.eta_global >= eta_target
        and r.deltaP <= dp_max
    ]

    if not valid:
        return None

    return max(
        valid,
        key=lambda r: (r.eta_global, -r.deltaP)
    )


# ============================================================
# APLICACIÓN
# ============================================================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(
            "Calculador de Ciclones V18 - SYCSAtech"
        )
        self.root.geometry("1500x920")
        self.root.minsize(1180, 760)

        self.current_page = "input"
        self.result = None
        self.structural_result = None
        self.psd_dp = None
        self.psd_weights = None
        self.comparison = []
        self.data = None

        # PSD medida introducida por el usuario:
        # [(diametro_um, porcentaje_masa), ...]
        self.psd_table_data = []
        self.psd_table_entries = []

        self.setup_styles()
        self.build_header()
        self.build_shell()
        self.build_pages()

        self.show_page("input")
        self.update_material()

    # --------------------------------------------------------
    # ESTILOS
    # --------------------------------------------------------

    def setup_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TCombobox",
            padding=5,
        )

        style.configure(
            "TEntry",
            padding=5,
        )

        style.configure(
            "Treeview",
            rowheight=28,
            font=tk_font(9),
        )

        style.configure(
            "Treeview.Heading",
            font=tk_font(9, weight="bold"),
        )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    def build_header(self):
        header = tk.Frame(
            self.root,
            bg=WHITE,
            height=112,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        logo_frame = tk.Frame(
            header,
            bg=WHITE,
        )
        logo_frame.pack(
            side="left",
            padx=18,
        )

        logo_path = (
            Path(__file__).resolve().parent
            / "SYCSA_TECH_logo.png"
        )

        if not logo_path.exists():
            logo_path = Path("/mnt/data/SYCSA_TECH_logo.png")

        if logo_path.exists() and PIL_AVAILABLE:
            try:
                image = Image.open(logo_path)
                image.thumbnail((390, 82))
                self.logo_img = ImageTk.PhotoImage(image)

                tk.Label(
                    logo_frame,
                    image=self.logo_img,
                    bg=WHITE,
                ).pack()
            except Exception:
                self.logo_fallback(logo_frame)
        else:
            self.logo_fallback(logo_frame)

        center = tk.Frame(
            header,
            bg=WHITE,
        )
        center.pack(
            side="left",
            expand=True,
        )

        tk.Label(
            center,
            text="CALCULADOR DE CICLONES",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(21, weight="bold"),
        ).pack(pady=(20, 1))

        tk.Label(
            center,
            text="Diseño, evaluación y optimización",
            bg=WHITE,
            fg=TEAL_DARK,
            font=tk_font(11),
        ).pack()

        actions = tk.Frame(
            header,
            bg=WHITE,
        )
        actions.pack(
            side="right",
            padx=20,
        )

        self.action_button(
            actions,
            "▣",
            "Informe",
            self.export_report,
        )
        self.action_button(
            actions,
            "▤",
            "Guardar",
            self.export_csv,
        )
        self.action_button(
            actions,
            "▱",
            "PDF",
            self.export_pdf,
        )
        self.action_button(
            actions,
            "ⓘ",
            "Acerca de",
            self.about,
        )

    def logo_fallback(self, parent):
        tk.Label(
            parent,
            text="SYCSAtech",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(28, weight="bold"),
        ).pack()

    def action_button(self, parent, icon, text, command):
        f = tk.Frame(parent, bg=WHITE)
        f.pack(side="left", padx=7)

        tk.Button(
            f,
            text=icon,
            command=command,
            bg=WHITE,
            fg=NAVY,
            bd=0,
            font=tk_font(19),
            cursor="hand2",
        ).pack()

        tk.Label(
            f,
            text=text,
            bg=WHITE,
            fg=NAVY,
            font=tk_font(8),
        ).pack()

    # --------------------------------------------------------
    # SHELL
    # --------------------------------------------------------

    def build_shell(self):
        self.sidebar = tk.Frame(
            self.root,
            bg=NAVY_DARK,
            width=250,
        )
        self.sidebar.pack(
            side="left",
            fill="y",
        )
        self.sidebar.pack_propagate(False)

        self.nav_buttons = {}

        nav = [
            ("input", "1", "Datos de Entrada", "Configure proceso y material"),
            ("results", "2", "Resultados", "Resumen general"),
            ("geometry", "3", "Geometría", "Dimensiones del ciclón"),
            ("particles", "4", "Análisis de Partículas", "Eficiencia vs tamaño"),
            ("comparison", "5", "Comparación Dc", "Análisis paramétrico"),
            ("recommendations", "6", "Recomendaciones", "Consejos de diseño"),
            ("structural", "7", "Diseño estructural", "Prediseño mecánico"),
            ("report", "8", "Informe", "Exportar resultados"),
        ]

        for page, number, title, subtitle in nav:
            self.add_nav(
                page,
                number,
                title,
                subtitle,
            )

        spacer = tk.Frame(
            self.sidebar,
            bg=NAVY_DARK,
        )
        spacer.pack(
            expand=True,
            fill="both",
        )

        help_box = tk.Frame(
            self.sidebar,
            bg=NAVY_LIGHT,
            padx=12,
            pady=12,
        )
        help_box.pack(
            fill="x",
            padx=12,
            pady=12,
        )

        tk.Label(
            help_box,
            text="¿Necesita ayuda?",
            bg=NAVY_LIGHT,
            fg=WHITE,
            font=tk_font(11, weight="bold"),
        ).pack(anchor="w")

        tk.Label(
            help_box,
            text=(
                "Ingrese primero los datos del proceso. "
                "Después navegue por Resultados, Geometría "
                "y Recomendaciones."
            ),
            bg=NAVY_LIGHT,
            fg="#DCE6F7",
            wraplength=210,
            justify="left",
            font=tk_font(8),
        ).pack(
            anchor="w",
            pady=7,
        )

        tk.Label(
            self.sidebar,
            text="SYCSAtech © 2026\nIngeniería que mueve tus ideas",
            bg=NAVY_DARK,
            fg="#B9C6E2",
            font=tk_font(8),
            justify="left",
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 10),
        )

        self.main = tk.Frame(
            self.root,
            bg=BG,
        )
        self.main.pack(
            side="left",
            fill="both",
            expand=True,
        )

    def add_nav(self, page, number, title, subtitle):
        frame = tk.Frame(
            self.sidebar,
            bg=NAVY_DARK,
            height=70,
            cursor="hand2",
        )
        frame.pack(
            fill="x",
        )
        frame.pack_propagate(False)

        badge = tk.Label(
            frame,
            text=number,
            bg=NAVY_LIGHT,
            fg=WHITE,
            width=3,
            font=tk_font(10, weight="bold"),
        )
        badge.pack(
            side="left",
            padx=(9, 10),
            pady=13,
        )

        text = tk.Frame(
            frame,
            bg=NAVY_DARK,
        )
        text.pack(
            side="left",
            fill="both",
            expand=True,
            pady=10,
        )

        title_label = tk.Label(
            text,
            text=title,
            bg=NAVY_DARK,
            fg=WHITE,
            font=tk_font(9, weight="bold"),
            anchor="w",
        )
        title_label.pack(fill="x")

        subtitle_label = tk.Label(
            text,
            text=subtitle,
            bg=NAVY_DARK,
            fg="#B9C6E2",
            font=tk_font(8),
            anchor="w",
        )
        subtitle_label.pack(fill="x")

        widgets = [
            frame,
            badge,
            text,
            title_label,
            subtitle_label,
        ]

        for w in widgets:
            w.bind(
                "<Button-1>",
                lambda e, p=page: self.show_page(p),
            )

        self.nav_buttons[page] = (
            frame,
            badge,
            title_label,
            subtitle_label,
        )

    # --------------------------------------------------------
    # PAGES
    # --------------------------------------------------------

    def build_pages(self):
        self.pages = {}

        for name in [
            "input",
            "results",
            "geometry",
            "particles",
            "comparison",
            "recommendations",
            "structural",
            "report",
        ]:
            frame = tk.Frame(
                self.main,
                bg=BG,
            )
            self.pages[name] = frame

        self.build_input_page()
        self.build_results_page()
        self.build_geometry_page()
        self.build_particles_page()
        self.build_comparison_page()
        self.build_recommendations_page()
        self.build_structural_page()
        self.build_report_page()

    def clear_page(self, page):
        for child in self.pages[page].winfo_children():
            child.destroy()

    def show_page(self, page):
        if page != "input" and self.result is None:
            if page in {
                "results",
                "geometry",
                "particles",
                "comparison",
                "recommendations",
                "structural",
                "report",
            }:
                messagebox.showinfo(
                    "Primero calcule",
                    "Ingrese los datos y presione CALCULAR antes "
                    "de abrir este módulo.",
                )
                page = "input"

        for frame in self.pages.values():
            frame.pack_forget()

        self.pages[page].pack(
            fill="both",
            expand=True,
        )

        self.current_page = page

        for name, controls in self.nav_buttons.items():
            frame, badge, title, subtitle = controls

            if name == page:
                frame.configure(bg=NAVY_LIGHT)
                badge.configure(bg=TEAL)
                title.configure(bg=NAVY_LIGHT)
                subtitle.configure(bg=NAVY_LIGHT)
            else:
                frame.configure(bg=NAVY_DARK)
                badge.configure(bg=NAVY_LIGHT)
                title.configure(bg=NAVY_DARK)
                subtitle.configure(bg=NAVY_DARK)

        if page == "results":
            self.refresh_results()
        elif page == "geometry":
            self.refresh_geometry()
        elif page == "particles":
            self.refresh_particles()
        elif page == "comparison":
            self.refresh_comparison()
        elif page == "recommendations":
            self.refresh_recommendations()
        elif page == "structural":
            self.refresh_structural()
        elif page == "report":
            self.refresh_report()

    # --------------------------------------------------------
    # COMMON PAGE
    # --------------------------------------------------------

    def page_header(self, parent, number, title, subtitle):
        h = tk.Frame(
            parent,
            bg=BG,
        )
        h.pack(
            fill="x",
            padx=20,
            pady=(18, 8),
        )

        tk.Label(
            h,
            text=number,
            bg=TEAL,
            fg=WHITE,
            font=tk_font(11, weight="bold"),
            width=3,
        ).pack(
            side="left",
            padx=(0, 10),
        )

        body = tk.Frame(
            h,
            bg=BG,
        )
        body.pack(side="left")

        tk.Label(
            body,
            text=title,
            bg=BG,
            fg=NAVY,
            font=tk_font(18, weight="bold"),
        ).pack(anchor="w")

        tk.Label(
            body,
            text=subtitle,
            bg=BG,
            fg=MUTED,
            font=tk_font(9),
        ).pack(anchor="w")

    def card(
        self,
        parent,
        title,
        width=None,
        side="left",
        fill="both",
        expand=True,
        padx=7,
        pady=2,
    ):
        # Card reutilizable. side/fill/expand permiten colocar una tarjeta
        # horizontal de ancho completo, por ejemplo para Opciones avanzadas,
        # sin cambiar el comportamiento de las tarjetas existentes.
        outer = tk.Frame(
            parent,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        if width:
            outer.configure(width=width)

        outer.pack(
            side=side,
            fill=fill,
            expand=expand,
            padx=padx,
            pady=pady,
        )

        header = tk.Frame(
            outer,
            bg=WHITE,
            padx=15,
            pady=5,
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text=title,
            bg=WHITE,
            fg=NAVY,
            font=tk_font(11, weight="bold"),
        ).pack(anchor="w")

        content = tk.Frame(
            outer,
            bg=WHITE,
            padx=15,
            pady=5,
        )
        content.pack(fill="both", expand=True)

        return content

    def field(self, parent, label, row, default, units=None):
        tk.Label(
            parent,
            text=label,
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=5,
        )

        holder = tk.Frame(
            parent,
            bg=WHITE,
        )
        holder.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=5,
        )

        entry = ttk.Entry(holder, width=16)
        entry.pack(
            side="left",
            fill="x",
            expand=True,
        )
        entry.insert(0, str(default))

        combo = None

        if units:
            combo = ttk.Combobox(
                holder,
                values=units,
                state="readonly",
                width=9,
            )
            combo.pack(
                side="left",
                padx=(5, 0),
            )
            combo.current(0)

        return entry, combo

    def compact_field(self, parent, label, row, col, default,
                     units=None, label_width=None):
        """Campo compacto para paneles horizontales de parámetros."""
        box = tk.Frame(
            parent,
            bg=WHITE,
        )
        box.grid(
            row=row,
            column=col,
            sticky="ew",
            padx=6,
            pady=4,
        )

        tk.Label(
            box,
            text=label,
            bg=WHITE,
            fg=NAVY,
            font=tk_font(8, weight="bold"),
        ).pack(
            anchor="w",
            pady=(0, 2),
        )

        holder = tk.Frame(
            box,
            bg=WHITE,
        )
        holder.pack(
            fill="x",
        )

        entry = ttk.Entry(
            holder,
            width=14,
        )
        entry.pack(
            side="left",
            fill="x",
            expand=True,
        )
        entry.insert(0, str(default))

        combo = None
        if units:
            combo = ttk.Combobox(
                holder,
                values=units,
                state="readonly",
                width=9,
            )
            combo.pack(
                side="left",
                padx=(4, 0),
            )
            combo.current(0)

        return entry, combo

    # --------------------------------------------------------
    # INPUT PAGE
    # --------------------------------------------------------

    def build_input_page(self):
        p = self.pages["input"]

        # ============================================================
        # CONTENEDOR SCROLLABLE — RESOLUCIONES DE PANTALLA
        # ============================================================
        # La página completa de entrada se desplaza verticalmente.
        # Esto evita que "Opciones avanzadas", CALCULAR y las notas queden
        # fuera de la pantalla en resoluciones pequeñas o con escalado DPI.
        # La barra permanece visible en el lado derecho.
        scroll_host = tk.Frame(p, bg=BG)
        scroll_host.pack(
            fill="both",
            expand=True,
        )

        canvas = tk.Canvas(
            scroll_host,
            bg=BG,
            highlightthickness=0,
            borderwidth=0,
            yscrollincrement=20,
        )
        scrollbar = ttk.Scrollbar(
            scroll_host,
            orient="vertical",
            command=canvas.yview,
        )

        canvas.configure(
            yscrollcommand=scrollbar.set,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )
        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scroll_content = tk.Frame(
            canvas,
            bg=BG,
        )
        window_id = canvas.create_window(
            (0, 0),
            window=scroll_content,
            anchor="nw",
        )

        def update_scroll_region(event=None):
            canvas.configure(
                scrollregion=canvas.bbox("all"),
            )

        def resize_scroll_content(event):
            # El contenido ocupa siempre el ancho visible del canvas,
            # evitando un scroll horizontal innecesario.
            canvas.itemconfigure(
                window_id,
                width=event.width,
            )
            canvas.configure(
                scrollregion=canvas.bbox("all"),
            )

        scroll_content.bind(
            "<Configure>",
            update_scroll_region,
        )
        canvas.bind(
            "<Configure>",
            resize_scroll_content,
        )

        def on_mousewheel(event):
            # Windows/macOS: delta. Linux: Button-4 / Button-5.
            if getattr(event, "delta", 0):
                canvas.yview_scroll(
                    int(-1 * (event.delta / 120)),
                    "units",
                )
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(3, "units")

        def bind_mousewheel(event=None):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            canvas.bind_all("<Button-4>", on_mousewheel)
            canvas.bind_all("<Button-5>", on_mousewheel)

        def unbind_mousewheel(event=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

        # Teclas rápidas para navegación vertical.
        def page_scroll(event):
            canvas.yview_scroll(
                -5 if event.keysym == "Prior" else 5,
                "units",
            )
            return "break"

        canvas.bind_all("<Prior>", page_scroll)
        canvas.bind_all("<Next>", page_scroll)

        # Guardamos referencias para evitar que se pierdan y para facilitar
        # futuras mejoras de la interfaz.
        self.input_scroll_canvas = canvas
        self.input_scrollbar = scrollbar
        self.input_scroll_content = scroll_content

        self.page_header(
            scroll_content,
            "1",
            "Datos de Entrada",
            "Configure el proceso, material, granulometría y diseño.",
        )

        area = tk.Frame(scroll_content, bg=BG)
        area.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5,
        )

        top = tk.Frame(area, bg=BG)
        top.pack(
            fill="x",
        )

        # Process
        c1 = self.card(
            top,
            "Proceso",
        )

        self.q, self.q_unit = self.field(
            c1,
            "Caudal de aire",
            0,
            "477",
            list(FLOW.keys()),
        )
        self.q_unit.set("CFM")

        self.temp, self.temp_unit = self.field(
            c1,
            "Temperatura",
            1,
            "25",
            ["°C", "K"],
        )
        self.temp_unit.set("°C")

        self.press, self.press_unit = self.field(
            c1,
            "Presión absoluta",
            2,
            "101.3",
            list(PRESSURE.keys()),
        )
        self.press_unit.set("kPa")

        tk.Label(
            c1,
            text="Propiedades del aire",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(15, 4),
        )

        self.air_status = tk.Label(
            c1,
            text="✓ AUTOMÁTICAS — determinadas por T y P",
            bg=TEAL_LIGHT,
            fg=TEAL_DARK,
            font=tk_font(8, weight="bold"),
            padx=8,
            pady=5,
        )
        self.air_status.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(2, 7),
        )

        self.rho_air_display = tk.StringVar(value="— kg/m³")
        self.mu_air_display = tk.StringVar(value="— Pa·s")

        tk.Label(
            c1, text="ρ aire", bg=WHITE, fg=MUTED,
            font=tk_font(8, weight="bold")
        ).grid(row=5, column=0, sticky="w", pady=4)
        tk.Label(
            c1, textvariable=self.rho_air_display, bg=WHITE, fg=TEXT,
            font=tk_font(10, weight="bold")
        ).grid(row=5, column=1, sticky="w", padx=(10, 0), pady=4)

        tk.Label(
            c1, text="μ aire", bg=WHITE, fg=MUTED,
            font=tk_font(8, weight="bold")
        ).grid(row=6, column=0, sticky="w", pady=4)
        tk.Label(
            c1, textvariable=self.mu_air_display, bg=WHITE, fg=TEXT,
            font=tk_font(10, weight="bold")
        ).grid(row=6, column=1, sticky="w", padx=(10, 0), pady=4)

        tk.Label(
            c1,
            text=("Solo ingrese la temperatura. La densidad se ajusta a la "
                  "presión absoluta indicada; la viscosidad depende de T."),
            bg=WHITE,
            fg=MUTED,
            justify="left",
            font=tk_font(8),
            wraplength=300,
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        # Particle
        c2 = self.card(
            top,
            "Partícula / Material",
        )

        tk.Label(
            c2,
            text="Material",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )

        self.material = ttk.Combobox(
            c2,
            values=list(MATERIALES.keys()),
            state="readonly",
            width=24,
        )
        self.material.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
            padx=(10, 0),
        )
        self.material.set("PET (Pellet)")
        self.material.bind(
            "<<ComboboxSelected>>",
            self.update_material,
        )

        self.rho_particle, _ = self.field(
            c2,
            "Densidad kg/m³",
            1,
            "1377.59",
        )

        self.dpg, self.dpg_unit = self.field(
            c2,
            "dpg",
            2,
            "3175",
            list(LENGTH.keys()),
        )
        self.dpg_unit.set("µm")

        self.sigma, _ = self.field(
            c2,
            "σg",
            3,
            "1.15",
        )

        tk.Label(
            c2,
            text="Distribución granulométrica",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(15, 4),
        )

        self.psd_mode = tk.StringVar(
            value="lognormal"
        )

        tk.Radiobutton(
            c2,
            text="Diámetro representativo único",
            variable=self.psd_mode,
            value="single",
            bg=WHITE,
            activebackground=WHITE,
            selectcolor=TEAL_LIGHT,
        ).grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="w",
        )

        tk.Radiobutton(
            c2,
            text="Distribución log-normal (recomendada)",
            variable=self.psd_mode,
            value="lognormal",
            bg=WHITE,
            activebackground=WHITE,
            selectcolor=TEAL_LIGHT,
            command=self.update_psd_mode_state,
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
        )

        tk.Radiobutton(
            c2,
            text="PSD medida — introducir tabla",
            variable=self.psd_mode,
            value="table",
            bg=WHITE,
            activebackground=WHITE,
            selectcolor=TEAL_LIGHT,
            command=self.update_psd_mode_state,
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.psd_table_button = tk.Button(
            c2,
            text="▦  Editar tabla de granulometría",
            command=self.open_psd_table,
            bg=WHITE,
            fg=NAVY,
            bd=1,
            relief="solid",
            font=tk_font(9, weight="bold"),
            cursor="hand2",
        )
        self.psd_table_button.grid(
            row=8,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(7, 4),
        )

        self.psd_table_status = tk.StringVar(
            value="Sin PSD medida cargada"
        )

        tk.Label(
            c2,
            textvariable=self.psd_table_status,
            bg=WHITE,
            fg=TEAL_DARK,
            font=tk_font(8, weight="bold"),
        ).grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="w",
        )

        tk.Label(
            c2,
            text=(
                "¿Para qué sirve la distribución granulométrica?\n"
                "Describe qué tamaños de partícula existen en el material. "
                "El ciclón no captura todas con la misma eficiencia: las finas "
                "son más difíciles de separar.\n"
                "Puede usar una distribución log-normal como aproximación o "
                "introducir una PSD medida en la tabla. Para la tabla se "
                "recomienda introducir diámetro de partícula (µm) y porcentaje "
                "en masa (%)."
            ),
            bg=TEAL_LIGHT,
            fg=TEXT,
            justify="left",
            wraplength=300,
            font=tk_font(8),
            padx=8,
            pady=7,
        ).grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 5),
        )

        tk.Button(
            c2,
            text="▱  Vista previa PSD",
            command=self.preview_psd,
            bg=WHITE,
            fg=NAVY,
            bd=1,
            relief="solid",
            font=tk_font(9, weight="bold"),
        ).grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=10,
        )

        # Design
        c3 = self.card(
            top,
            "Diseño",
        )

        tk.Label(
            c3,
            text="Tipo de ciclón",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )

        self.cyclone_type = ttk.Combobox(
            c3,
            values=[
                "Stairmand (EPA)",
                "Lapple",
            ],
            state="readonly",
            width=23,
        )
        self.cyclone_type.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
            padx=(10, 0),
        )
        self.cyclone_type.set(
            "Stairmand (EPA)"
        )

        self.Dc, self.Dc_unit = self.field(
            c3,
            "Diámetro Dc",
            1,
            "0.70",
            list(LENGTH.keys()),
        )
        self.Dc_unit.set("m")

        self.n_cyclones, _ = self.field(
            c3,
            "Ciclones en paralelo",
            2,
            "1",
        )

        self.Ne, _ = self.field(
            c3,
            "Vueltas efectivas Ne",
            3,
            "5",
        )

        tk.Label(
            area,
            text="↕ Desplácese verticalmente para ver todas las opciones y el botón CALCULAR.",
            bg=TEAL_LIGHT,
            fg=TEAL_DARK,
            font=tk_font(8, weight="bold"),
            padx=8,
            pady=5,
        ).pack(
            fill="x",
            pady=(4, 2),
        )

        # Advanced
        # ------------------------------------------------------------
        # Distribución compacta:
        # 3 columnas x 3 filas + ayuda + CALCULAR.
        # La página completa tiene desplazamiento vertical, por lo que
        # todos los campos siguen siendo accesibles en cualquier resolución.
        # ------------------------------------------------------------
        c4 = self.card(
            area,
            "Opciones avanzadas",
            side="top",
            fill="x",
            expand=False,
            padx=0,
            pady=5,
        )

        for col in range(3):
            c4.columnconfigure(col, weight=1, uniform="advanced")

        # Fila 0
        self.K_loss, _ = self.compact_field(
            c4, "Factor K ΔP", 0, 0, "7"
        )
        self.vmin, _ = self.compact_field(
            c4, "V mínima [m/s]", 0, 1, "12"
        )
        self.vmax, _ = self.compact_field(
            c4, "V máxima [m/s]", 0, 2, "25"
        )

        # Fila 1
        self.eta_target, _ = self.compact_field(
            c4, "Eficiencia objetivo [%]", 1, 0, "90"
        )
        self.dp_max, _ = self.compact_field(
            c4, "ΔP máxima [Pa]", 1, 1, "2500"
        )
        self.compare_range, _ = self.compact_field(
            c4, "Dc para comparar [m]", 1, 2,
            "0.4,0.5,0.6,0.7,0.8,1.0"
        )

        # Fila 2 — material, condición y presión/vacío
        material_box = tk.Frame(c4, bg=WHITE)
        material_box.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=6,
            pady=4,
        )

        tk.Label(
            material_box,
            text="Material de construcción CAD",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(8, weight="bold"),
        ).pack(
            anchor="w",
            pady=(0, 2),
        )

        self.construction_material = ttk.Combobox(
            material_box,
            values=[
                "Acero al carbón",
                "Acero inoxidable 304",
                "Acero inoxidable 316",
                "Aluminio 5052",
                "Aluminio 6061",
            ],
            state="readonly",
        )
        self.construction_material.pack(
            fill="x",
        )
        self.construction_material.set("Acero al carbón")

        mode_box = tk.Frame(c4, bg=WHITE)
        mode_box.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=6,
            pady=4,
        )

        tk.Label(
            mode_box,
            text="Condición mecánica",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(8, weight="bold"),
        ).pack(
            anchor="w",
            pady=(0, 2),
        )

        self.pressure_mode = tk.StringVar(value="Vacío")

        mode_frame = tk.Frame(
            mode_box,
            bg=WHITE,
        )
        mode_frame.pack(
            fill="x",
        )

        tk.Radiobutton(
            mode_frame,
            text="Vacío",
            variable=self.pressure_mode,
            value="Vacío",
            bg=WHITE,
            activebackground=WHITE,
            selectcolor=TEAL_LIGHT,
            font=tk_font(8),
        ).pack(
            side="left",
            padx=(0, 8),
        )

        tk.Radiobutton(
            mode_frame,
            text="Presión",
            variable=self.pressure_mode,
            value="Presión",
            bg=WHITE,
            activebackground=WHITE,
            selectcolor=TEAL_LIGHT,
            font=tk_font(8),
        ).pack(
            side="left",
        )

        pressure_box = tk.Frame(c4, bg=WHITE)
        pressure_box.grid(
            row=2,
            column=2,
            sticky="ew",
            padx=6,
            pady=4,
        )

        tk.Label(
            pressure_box,
            text="Presión/vacío de diseño",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(8, weight="bold"),
        ).pack(
            anchor="w",
            pady=(0, 2),
        )

        pressure_holder = tk.Frame(
            pressure_box,
            bg=WHITE,
        )
        pressure_holder.pack(
            fill="x",
        )

        self.design_pressure = ttk.Entry(
            pressure_holder,
            width=12,
        )
        self.design_pressure.pack(
            side="left",
            fill="x",
            expand=True,
        )
        self.design_pressure.insert(0, "8")

        self.design_pressure_unit = ttk.Combobox(
            pressure_holder,
            values=["kPa", "bar", "psi", "inH₂O", "inHg"],
            state="readonly",
            width=8,
        )
        self.design_pressure_unit.pack(
            side="left",
            padx=(4, 0),
        )
        self.design_pressure_unit.set("inHg")

        # Nota compacta
        tk.Label(
            c4,
            text=(
                "Estos parámetros controlan la selección de geometría, "
                "pérdida de presión y prediseño mecánico. "
                "La presión/vacío de diseño es independiente de la presión "
                "absoluta utilizada para calcular las propiedades del aire."
            ),
            bg=TEAL_LIGHT,
            fg=TEXT,
            justify="left",
            wraplength=1100,
            font=tk_font(8),
            padx=8,
            pady=6,
        ).grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=6,
            pady=(3, 5),
        )

        tk.Button(
            c4,
            text="▶  CALCULAR",
            command=self.calculate_gui,
            bg=TEAL,
            fg=WHITE,
            activebackground=TEAL_DARK,
            activeforeground=WHITE,
            bd=0,
            padx=12,
            pady=7,
            font=tk_font(9, weight="bold"),
            cursor="hand2",
        ).grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=6,
            pady=(0, 5),
        )

        # Guidance
        guidance = tk.Frame(
            area,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        guidance.pack(
            fill="x",
            pady=12,
        )

        tk.Label(
            guidance,
            text="¿CÓMO INGRESAR LOS DATOS?",
            bg=NAVY,
            fg=WHITE,
            font=tk_font(11, weight="bold"),
            anchor="w",
            padx=12,
            pady=7,
        ).pack(fill="x")

        text = (
            "① Caudal: ingrese el caudal volumétrico y seleccione su unidad.  "
            "② Temperatura y presión: use presión absoluta.  "
            "③ Material: seleccione de la biblioteca o personalice densidad y dpg.  "
            "④ Granulometría: para polvos use distribución log-normal.  "
            "⑤ Diseño: seleccione la geometría, Dc y número de ciclones.  "
            "⑥ La entrada circular se dimensiona a partir del área rectangular "
            "equivalente y se recomienda transición tangencial.  "
            "⑦ Presione CALCULAR y revise Resultados y Recomendaciones."
        )

        tk.Label(
            guidance,
            text=text,
            bg=WHITE,
            fg=MUTED,
            justify="left",
            wraplength=1100,
            font=tk_font(9),
            padx=12,
            pady=10,
        ).pack(
            fill="x",
        )

    # --------------------------------------------------------
    # RESULTS PAGE
    # --------------------------------------------------------

    def build_results_page(self):
        p = self.pages["results"]

        self.page_header(
            p,
            "2",
            "Resultados",
            "Resumen general del punto de diseño calculado.",
        )

        self.results_container = tk.Frame(
            p,
            bg=BG,
        )
        self.results_container.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5,
        )

    def refresh_results(self):
        for w in self.results_container.winfo_children():
            w.destroy()

        if not self.result:
            return

        r = self.result
        d = self.data

        metrics = [
            ("Eficiencia global", f"{r.eta_global*100:.2f} %", TEAL),
            ("Diámetro de corte", f"{r.dpc*1e6:.2f} µm", ORANGE),
            ("Velocidad de entrada", f"{r.V_in:.2f} m/s", NAVY),
            ("Pérdida de presión", f"{r.deltaP:.0f} Pa", PURPLE),
            ("Can velocity", f"{r.V_can:.2f} m/s", TEAL_DARK),
            ("Reynolds", f"{r.Reynolds:.2e}", NAVY),
        ]

        grid = tk.Frame(
            self.results_container,
            bg=BG,
        )
        grid.pack(
            fill="x",
        )

        for i, (name, value, color) in enumerate(metrics):
            box = tk.Frame(
                grid,
                bg=WHITE,
                highlightbackground=BORDER,
                highlightthickness=1,
                padx=15,
                pady=12,
            )
            box.grid(
                row=i // 3,
                column=i % 3,
                sticky="nsew",
                padx=5,
                pady=5,
            )

            tk.Label(
                box,
                text=name,
                bg=WHITE,
                fg=MUTED,
                font=tk_font(9),
            ).pack(anchor="w")

            tk.Label(
                box,
                text=value,
                bg=WHITE,
                fg=color,
                font=tk_font(18, weight="bold"),
            ).pack(anchor="w", pady=(3, 0))

        for col in range(3):
            grid.columnconfigure(col, weight=1)

        detail = self.card(
            self.results_container,
            "Resumen del diseño",
        )
        detail.pack(
            fill="x",
            pady=10,
        )

        g = r.geometry

        rows = [
            ("Material", d["material"]),
            ("Geometría", g.name),
            ("Caudal total", f"{d['Q']:.6f} m³/s"),
            ("Caudal por ciclón", f"{r.Q_cyclone:.6f} m³/s"),
            ("Dc", f"{r.Dc:.4f} m"),
            ("a", f"{g.a:.4f} m"),
            ("b", f"{g.b:.4f} m"),
            ("De", f"{g.De:.4f} m"),
            ("S", f"{g.S:.4f} m"),
            ("h", f"{g.h:.4f} m"),
            ("H", f"{g.H:.4f} m"),
            ("B", f"{g.B:.4f} m"),
        ]

        for i, (label, value) in enumerate(rows):
            tk.Label(
                detail,
                text=label,
                bg=WHITE,
                fg=MUTED,
                font=tk_font(9, weight="bold"),
            ).grid(
                row=i // 4,
                column=(i % 4) * 2,
                sticky="w",
                padx=8,
                pady=4,
            )

            tk.Label(
                detail,
                text=value,
                bg=WHITE,
                fg=TEXT,
                font=tk_font(9),
            ).grid(
                row=i // 4,
                column=(i % 4) * 2 + 1,
                sticky="w",
                padx=(0, 15),
                pady=4,
            )

    # --------------------------------------------------------
    # GEOMETRY PAGE
    # --------------------------------------------------------

    def build_geometry_page(self):
        p = self.pages["geometry"]

        self.page_header(
            p,
            "3",
            "Geometría",
            "Dimensiones calculadas a partir del diámetro Dc.",
        )

        self.geometry_content = tk.Frame(
            p,
            bg=BG,
        )
        self.geometry_content.pack(
            fill="both",
            expand=True,
            padx=20,
        )

    def refresh_geometry(self):
        for w in self.geometry_content.winfo_children():
            w.destroy()

        r = self.result

        if not r:
            return

        left = self.card(
            self.geometry_content,
            "Dimensiones",
        )
        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 7),
        )

        g = r.geometry

        inlet_rec = inlet_pipe_recommendation(r)

        rows = [
            ("Dc - diámetro ciclón", r.Dc),
            ("a - ancho entrada", g.a),
            ("b - altura entrada", g.b),
            ("Ae - área entrada", inlet_rec["area_rect_m2"]),
            ("Deq - tubo circular equivalente", inlet_rec["deq_m"]),
            ("De - vortex finder", g.De),
            ("S - profundidad", g.S),
            ("h - cuerpo cilíndrico", g.h),
            ("H - altura total", g.H),
            ("B - salida de sólidos", g.B),
        ]

        for i, (label, value) in enumerate(rows):
            tk.Label(
                left,
                text=label,
                bg=WHITE,
                fg=NAVY,
                font=tk_font(9, weight="bold"),
            ).grid(
                row=i,
                column=0,
                sticky="w",
                pady=7,
            )

            tk.Label(
                left,
                text=f"{value:.5f} m",
                bg=WHITE,
                fg=TEXT,
                font=tk_font(10),
            ).grid(
                row=i,
                column=1,
                sticky="w",
                padx=15,
            )

        right = self.card(
            self.geometry_content,
            "Esquema dimensional",
        )
        right.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(7, 0),
        )

        self.draw_geometry_canvas(
            right,
            r,
        )

        tk.Label(
            right,
            text="DETALLE DE ENTRADA CIRCULAR — PROPUESTA PARA CAD",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(10, weight="bold"),
            pady=5,
        ).pack(
            fill="x",
            pady=(6, 0),
        )

        self.draw_inlet_detail_canvas(
            right,
            r,
        )

        inlet_rec = inlet_pipe_recommendation(r)
        pipe_box = tk.Frame(
            right,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        pipe_box.pack(
            fill="x",
            pady=(4, 0),
        )

        tk.Label(
            pipe_box,
            text="BIBLIOTECA DE TUBERÍAS — ENTRADA CIRCULAR",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).pack(anchor="w")

        pipe_rec = pipe_candidates(
            r,
            self.data.get("construction_material", "Acero al carbón"),
            float(self.vmin.get()),
            float(self.vmax.get()),
        )

        if pipe_rec["available"]:
            sel = pipe_rec["selected"]
            tk.Label(
                pipe_box,
                text=(
                    f"{'✓' if pipe_rec['status']=='CUMPLE' else '⚠'} "
                    f"{pipe_rec['status']}: NPS {sel['nps']} / DN {sel['dn']} — "
                    f"Schedule {sel['schedule']}  |  "
                    f"OD {sel['od_mm']:.1f} mm  |  "
                    f"t {sel['wall_mm']:.2f} mm  |  "
                    f"ID {sel['id_mm']:.1f} mm  |  "
                    f"V {sel['velocity_m_s']:.2f} m/s"
                ),
                bg=TEAL_LIGHT,
                fg=GREEN if pipe_rec["status"] == "CUMPLE" else ORANGE,
                wraplength=700,
                justify="left",
                font=tk_font(8, weight="bold"),
                padx=8,
                pady=6,
            ).pack(fill="x", pady=(5, 4))

            tk.Label(
                pipe_box,
                text=(
                    f"Deq = {pipe_rec['deq_m']*1000:.1f} mm  |  "
                    f"V geométrica = {pipe_rec['velocity_equivalent_m_s']:.2f} m/s  |  "
                    f"Base dimensional: {pipe_rec['standard']}.\n"
                    f"{pipe_rec['selection_basis']} {pipe_rec['conflict_message']}"
                ),
                bg=WHITE,
                fg=MUTED,
                wraplength=700,
                justify="left",
                font=tk_font(8),
            ).pack(anchor="w")

            # Compact table of the nearest commercial alternatives.
            nearest = sorted(
                pipe_rec["candidates"],
                key=lambda c: abs(c["id_mm"] - pipe_rec["deq_m"]*1000)
            )[:4]

            table = tk.Frame(pipe_box, bg=WHITE)
            table.pack(fill="x", pady=(5, 0))

            headers = ["NPS", "Sch", "OD", "t", "ID", "V"]
            for j, htxt in enumerate(headers):
                tk.Label(
                    table,
                    text=htxt,
                    bg=NAVY,
                    fg=WHITE,
                    font=tk_font(7, weight="bold"),
                    padx=5,
                    pady=3,
                ).grid(row=0, column=j, sticky="ew")

            for i, c in enumerate(nearest, 1):
                vals = [
                    f"{c['nps']} / DN{c['dn']}",
                    c["schedule"],
                    f"{c['od_mm']:.1f}",
                    f"{c['wall_mm']:.2f}",
                    f"{c['id_mm']:.1f}",
                    f"{c['velocity_m_s']:.2f}",
                ]
                for j, val in enumerate(vals):
                    tk.Label(
                        table,
                        text=val,
                        bg=TEAL_LIGHT if c["recommended"] else WHITE,
                        fg=NAVY if c["recommended"] else TEXT,
                        font=tk_font(7, weight="bold" if c["recommended"] else None),
                        padx=5,
                        pady=2,
                    ).grid(row=i, column=j, sticky="ew")

            tk.Label(
                pipe_box,
                text=(
                    "La biblioteca dimensiona el diámetro y la velocidad de la "
                    "línea. El espesor de la tubería debe verificarse por presión, "
                    "vacío, soportes y código aplicable. Para la entrada del ciclón "
                    "se mantiene la transición circular → tangencial."
                ),
                bg=TEAL_LIGHT,
                fg=TEXT,
                wraplength=700,
                justify="left",
                font=tk_font(7),
                padx=7,
                pady=5,
            ).pack(fill="x", pady=(5, 0))
        else:
            tk.Label(
                pipe_box,
                text=pipe_rec["message"],
                bg=TEAL_LIGHT,
                fg=NAVY,
                wraplength=700,
                justify="left",
                font=tk_font(8, weight="bold"),
                padx=8,
                pady=7,
            ).pack(fill="x", pady=(5, 0))

    def draw_geometry_canvas(self, parent, r):
        """Dibuja un esquema dimensional del ciclón, inspirado en el
        esquema de referencia proporcionado por el usuario. Las
        proporciones corresponden a las relaciones geométricas calculadas."""
        canvas = tk.Canvas(
            parent,
            bg=WHITE,
            height=400,
            highlightthickness=0,
        )
        canvas.pack(
            fill="both",
            expand=True,
        )

        g = r.geometry
        Dc = r.Dc
        H = g.H
        h = g.h
        cone_h = max(H - h, 1e-9)
        B = g.B
        De = g.De
        S = g.S
        a = g.a
        b = g.b

        canvas.update_idletasks()
        W = max(canvas.winfo_width(), 700)
        Hpx = max(canvas.winfo_height(), 560)

        # Escala para que el ciclón ocupe el área disponible.
        scale = min(
            260 / max(Dc, 1e-6),
            330 / max(H, 1e-6),
        )

        cx = int(W * 0.58)
        top = 45
        body_h = h * scale
        cone_h_px = cone_h * scale
        body_bottom = top + body_h
        bottom = body_bottom + cone_h_px
        half = Dc * scale / 2

        # Cuerpo
        canvas.create_rectangle(
            cx - half,
            top + 25,
            cx + half,
            body_bottom,
            outline=NAVY,
            fill="#DDF3FA",
            width=2,
        )

        # Cono
        canvas.create_polygon(
            cx - half,
            body_bottom,
            cx + half,
            body_bottom,
            cx + B * scale / 2,
            bottom,
            cx - B * scale / 2,
            bottom,
            outline=NAVY,
            fill="#BFE7F3",
            width=2,
        )

        # Vortex finder / salida de gas
        vf_half = De * scale / 2
        vf_top = top
        vf_bottom = top + S * scale

        canvas.create_rectangle(
            cx - vf_half,
            vf_top,
            cx + vf_half,
            vf_bottom,
            outline=TEAL_DARK,
            fill="#5EC0D2",
            width=2,
        )

        # Elipse superior
        canvas.create_oval(
            cx - vf_half,
            vf_top - 8,
            cx + vf_half,
            vf_top + 8,
            outline=NAVY,
            fill="#DDF3FA",
            width=2,
        )

        # Entrada tangencial
        inlet_x0 = cx - half - a * scale
        inlet_y = top + 25 + b * scale * 0.55

        canvas.create_rectangle(
            inlet_x0,
            inlet_y - b * scale / 2,
            cx - half,
            inlet_y + b * scale / 2,
            outline=NAVY,
            fill="#8BD4E5",
            width=2,
        )

        # Flecha de entrada
        canvas.create_line(
            inlet_x0 + 12,
            inlet_y,
            cx - half - 7,
            inlet_y,
            arrow=tk.LAST,
            fill=NAVY_DARK,
            width=3,
        )

        # Trayectoria helicoidal simplificada
        pts = []
        turns = 2.7
        npts = 180
        radius = max(half * 0.74, 15)

        for i in range(npts):
            t = i / (npts - 1)
            ang = 2 * math.pi * turns * t
            x = cx + radius * math.cos(ang)
            y = (top + 75) + (body_bottom - (top + 75)) * t
            pts.extend([x, y])

        canvas.create_line(
            *pts,
            fill="#26384A",
            dash=(7, 4),
            width=2,
            smooth=True,
        )

        # Flechas sobre la trayectoria
        for frac in (0.22, 0.48, 0.74):
            idx = int(frac * (npts - 1))
            idx2 = min(idx + 2, npts - 1)
            x1 = pts[2 * idx]
            y1 = pts[2 * idx + 1]
            x2 = pts[2 * idx2]
            y2 = pts[2 * idx2 + 1]
            canvas.create_line(
                x1, y1, x2, y2,
                arrow=tk.LAST,
                fill="#26384A",
                width=2,
            )

        # Partículas
        for frac in (0.27, 0.60, 0.86):
            idx = int(frac * (npts - 1))
            px = pts[2 * idx] + 9
            py = pts[2 * idx + 1]
            for dx, dy in ((0,0), (7,-5), (-6,5), (5,7)):
                canvas.create_oval(
                    px + dx - 2,
                    py + dy - 2,
                    px + dx + 2,
                    py + dy + 2,
                    fill=NAVY_DARK,
                    outline=NAVY_DARK,
                )

        # Salida de sólidos
        canvas.create_line(
            cx - B * scale / 2,
            bottom,
            cx + B * scale / 2,
            bottom,
            fill=NAVY,
            width=2,
        )

        # Helper de cotas
        def dim_h(x1, x2, y, label, color=NAVY):
            canvas.create_line(
                x1, y, x2, y,
                fill=color,
                width=1,
                arrow=tk.BOTH,
            )
            canvas.create_line(
                x1, y - 6, x1, y + 6,
                fill=color,
            )
            canvas.create_line(
                x2, y - 6, x2, y + 6,
                fill=color,
            )
            canvas.create_text(
                (x1 + x2) / 2,
                y - 11,
                text=label,
                fill=color,
                font=tk_font(8, weight="bold"),
            )

        def dim_v(x, y1, y2, label, color=NAVY):
            canvas.create_line(
                x, y1, x, y2,
                fill=color,
                width=1,
                arrow=tk.BOTH,
            )
            canvas.create_line(
                x - 6, y1, x + 6, y1,
                fill=color,
            )
            canvas.create_line(
                x - 6, y2, x + 6, y2,
                fill=color,
            )
            canvas.create_text(
                x + 34,
                (y1 + y2) / 2,
                text=label,
                fill=color,
                font=tk_font(8, weight="bold"),
                angle=90,
            )

        # Cotas principales
        dim_h(
            cx - half,
            cx + half,
            bottom + 42,
            f"Dc = {Dc:.3f} m",
        )

        dim_h(
            cx - vf_half,
            cx + vf_half,
            top - 25,
            f"De = {De:.3f} m",
            TEAL_DARK,
        )

        dim_v(
            cx + half + 55,
            top + 25,
            body_bottom,
            f"h = {h:.3f} m",
        )

        dim_v(
            cx + half + 95,
            body_bottom,
            bottom,
            f"H-h = {cone_h:.3f} m",
        )

        dim_v(
            cx + half + 135,
            top + 25,
            bottom,
            f"H = {H:.3f} m",
        )

        # Entrada
        canvas.create_text(
            inlet_x0 - 25,
            inlet_y - b * scale / 2 - 16,
            text=f"a = {a:.3f} m",
            fill=TEAL_DARK,
            font=tk_font(8, weight="bold"),
        )

        canvas.create_text(
            inlet_x0 - 25,
            inlet_y + b * scale / 2 + 14,
            text=f"b = {b:.3f} m",
            fill=TEAL_DARK,
            font=tk_font(8, weight="bold"),
        )

        canvas.create_text(
            cx + vf_half + 45,
            vf_bottom,
            text=f"S = {S:.3f} m",
            fill=TEAL_DARK,
            font=tk_font(8, weight="bold"),
        )

        canvas.create_text(
            cx,
            bottom + 65,
            text=f"B = {B:.3f} m",
            fill=NAVY,
            font=tk_font(8, weight="bold"),
        )

        canvas.create_text(
            15,
            Hpx - 18,
            anchor="w",
            text=(
                "Esquema ilustrativo. Las proporciones se generan a partir "
                f"de la geometría {g.name}; verificar tolerancias y espesores "
                "antes de fabricar."
            ),
            fill=MUTED,
            font=tk_font(8),
        )


    def draw_inlet_detail_canvas(self, parent, r):
        """
        Dibuja un detalle de ingeniería de la transición de una tubería circular
        hacia la entrada tangencial rectangular del ciclón.

        El diámetro circular se obtiene conservando, en primera aproximación,
        el área de entrada:
            Deq = sqrt(4*a*b/pi)

        La propuesta NO implica que una conexión circular sea idéntica a la
        entrada Stairmand rectangular; se requiere transición y verificación
        de pérdidas/velocidad.
        """
        rec = inlet_pipe_recommendation(r)
        g = r.geometry

        canvas = tk.Canvas(
            parent,
            bg=WHITE,
            height=250,
            highlightthickness=0,
        )
        canvas.pack(
            fill="x",
            expand=False,
        )
        canvas.update_idletasks()

        W = max(canvas.winfo_width(), 650)
        Hpx = 250

        # Cuerpo del ciclón visto en planta.
        cx = int(W * 0.70)
        cy = 125
        radius = 72

        canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=NAVY,
            fill="#DDF3FA",
            width=3,
        )

        # Entrada tangencial rectangular.
        inlet_left = cx - radius - 95
        inlet_top = cy - 24
        inlet_bottom = cy + 24

        canvas.create_rectangle(
            inlet_left,
            inlet_top,
            cx - radius,
            inlet_bottom,
            outline=NAVY,
            fill="#8BD4E5",
            width=2,
        )

        # Transición circular-tangencial.
        pipe_center = (inlet_left - 95, cy)
        pipe_r = 34

        canvas.create_oval(
            pipe_center[0] - pipe_r,
            pipe_center[1] - pipe_r,
            pipe_center[0] + pipe_r,
            pipe_center[1] + pipe_r,
            outline=TEAL_DARK,
            fill="#BFE7F3",
            width=3,
        )

        # Transición visual.
        canvas.create_polygon(
            pipe_center[0] + pipe_r,
            pipe_center[1] - pipe_r,
            inlet_left,
            inlet_top,
            inlet_left,
            inlet_bottom,
            pipe_center[0] + pipe_r,
            pipe_center[1] + pipe_r,
            outline=TEAL_DARK,
            fill="#CFEFF6",
            width=2,
        )

        # Flujo.
        canvas.create_line(
            pipe_center[0] - 55,
            cy,
            inlet_left + 15,
            cy,
            arrow=tk.LAST,
            fill=NAVY_DARK,
            width=3,
        )
        canvas.create_line(
            inlet_left + 10,
            cy,
            cx - radius + 15,
            cy,
            arrow=tk.LAST,
            fill=NAVY_DARK,
            width=3,
        )

        # Cotas.
        canvas.create_text(
            pipe_center[0],
            cy - pipe_r - 18,
            text=f"Deq = {rec['deq_m']*1000:.1f} mm",
            fill=TEAL_DARK,
            font=tk_font(9, weight="bold"),
        )

        canvas.create_text(
            inlet_left + 35,
            inlet_top - 15,
            text=f"a = {g.a*1000:.1f} mm",
            fill=NAVY,
            font=tk_font(8, weight="bold"),
        )

        canvas.create_text(
            inlet_left + 35,
            inlet_bottom + 15,
            text=f"b = {g.b*1000:.1f} mm",
            fill=NAVY,
            font=tk_font(8, weight="bold"),
        )

        canvas.create_text(
            cx,
            cy + radius + 25,
            text="Entrada tangencial al cuerpo del ciclón",
            fill=NAVY,
            font=tk_font(9, weight="bold"),
        )

        canvas.create_text(
            15,
            20,
            anchor="w",
            text="Tubería circular",
            fill=TEAL_DARK,
            font=tk_font(9, weight="bold"),
        )

        canvas.create_text(
            15,
            42,
            anchor="w",
            text="Calibrada o Schedule 10/10S",
            fill=TEXT,
            font=tk_font(9),
        )

        canvas.create_text(
            15,
            72,
            anchor="w",
            text=(
                "Recomendación: conservar aproximadamente el área Ae = a·b "
                "y usar una transición circular → tangencial."
            ),
            fill=MUTED,
            width=310,
            justify="left",
            font=tk_font(8),
        )

        canvas.create_text(
            15,
            180,
            anchor="w",
            text=(
                "La tubería no debe conectarse directamente como un orificio "
                "circular sin transición: la geometría de separación calculada "
                "se basa en una entrada tangencial."
            ),
            fill=ORANGE,
            width=330,
            justify="left",
            font=tk_font(8, weight="bold"),
        )

        return canvas

    # --------------------------------------------------------
    # PARTICLE PAGE
    # --------------------------------------------------------

    def build_particles_page(self):
        p = self.pages["particles"]

        self.page_header(
            p,
            "4",
            "Análisis de Partículas",
            "Evalúe la eficiencia de captura en función del tamaño.",
        )

        self.particle_content = tk.Frame(
            p,
            bg=BG,
        )
        self.particle_content.pack(
            fill="both",
            expand=True,
            padx=20,
        )

    def refresh_particles(self):
        for w in self.particle_content.winfo_children():
            w.destroy()

        if not self.result:
            return

        top = self.card(
            self.particle_content,
            "Resumen de separación",
        )
        top.pack(
            fill="x",
        )

        r = self.result

        values = [
            ("dpc", f"{r.dpc*1e6:.2f} µm"),
            ("Eficiencia global", f"{r.eta_global*100:.2f}%"),
            ("dpg", f"{self.data['dpg_m']*1e6:.2f} µm"),
            ("σg", f"{self.data['sigma']:.2f}"),
        ]

        for i, (name, value) in enumerate(values):
            tk.Label(
                top,
                text=name,
                bg=WHITE,
                fg=MUTED,
                font=tk_font(9),
            ).grid(
                row=0,
                column=i * 2,
                padx=10,
                pady=4,
                sticky="w",
            )
            tk.Label(
                top,
                text=value,
                bg=WHITE,
                fg=NAVY,
                font=tk_font(12, weight="bold"),
            ).grid(
                row=0,
                column=i * 2 + 1,
                padx=(0, 20),
                pady=4,
                sticky="w",
            )

        graph = self.card(
            self.particle_content,
            "Curva de eficiencia",
        )
        graph.pack(
            fill="both",
            expand=True,
            pady=10,
        )

        tk.Button(
            graph,
            text="Abrir gráfica de eficiencia",
            command=self.plot_particle_analysis,
            bg=TEAL,
            fg=WHITE,
            bd=0,
            font=tk_font(10, weight="bold"),
            padx=12,
            pady=8,
        ).pack(
            pady=15,
        )

        tk.Label(
            graph,
            text=(
                "Interpretación: a medida que el tamaño de partícula "
                "disminuye por debajo de dpc, la eficiencia de captura "
                "tiende a disminuir. Para polvos finos, utilice una PSD "
                "real y considere una etapa de filtración posterior."
            ),
            bg=WHITE,
            fg=MUTED,
            wraplength=900,
            justify="left",
            font=tk_font(10),
        ).pack(
            padx=15,
            pady=10,
        )

    def plot_particle_analysis(self):
        dp = np.logspace(-1, 4, 400)
        eta = fractional_efficiency(
            dp * 1e-6,
            self.result.dpc,
        )

        plt.figure(
            figsize=(9, 6)
        )
        plt.semilogx(
            dp,
            eta * 100,
            linewidth=2,
            label="Eficiencia fraccional",
        )

        plt.axvline(
            self.result.dpc * 1e6,
            linestyle="--",
            label=f"dpc = {self.result.dpc*1e6:.1f} µm",
        )

        plt.axvline(
            self.data["dpg_m"] * 1e6,
            linestyle=":",
            label=f"dpg = {self.data['dpg_m']*1e6:.1f} µm",
        )

        plt.xlabel(
            "Diámetro de partícula (µm)"
        )
        plt.ylabel(
            "Eficiencia de captura (%)"
        )
        plt.title(
            f"Análisis de partículas - {self.data['material']}"
        )
        plt.grid(
            True,
            which="both",
            alpha=0.3,
        )
        plt.legend()
        plt.tight_layout()
        plt.show()

    # --------------------------------------------------------
    # COMPARISON PAGE
    # --------------------------------------------------------

    def build_comparison_page(self):
        p = self.pages["comparison"]

        self.page_header(
            p,
            "5",
            "Comparación de Dc",
            "Compare diferentes diámetros y seleccione un candidato preliminar.",
        )

        self.comparison_content = tk.Frame(
            p,
            bg=BG,
        )
        self.comparison_content.pack(
            fill="both",
            expand=True,
            padx=20,
        )

    def refresh_comparison(self):
        for w in self.comparison_content.winfo_children():
            w.destroy()

        if not self.result:
            return

        controls = self.card(
            self.comparison_content,
            "Análisis paramétrico",
        )
        controls.pack(
            fill="x",
        )

        tk.Label(
            controls,
            text="Dc a comparar (m):",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(9, weight="bold"),
        ).pack(
            side="left",
            padx=5,
        )

        entry = ttk.Entry(
            controls,
            width=50,
        )
        entry.pack(
            side="left",
            padx=8,
        )
        entry.insert(
            0,
            self.compare_range.get(),
        )

        tk.Button(
            controls,
            text="Comparar",
            command=lambda: self.run_comparison(entry.get()),
            bg=TEAL,
            fg=WHITE,
            bd=0,
            font=tk_font(9, weight="bold"),
            padx=10,
            pady=6,
        ).pack(
            side="left",
        )

        table_frame = tk.Frame(
            self.comparison_content,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        table_frame.pack(
            fill="both",
            expand=True,
            pady=10,
        )

        columns = (
            "Dc",
            "V",
            "Can",
            "dpc",
            "eta",
            "dP",
        )

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "Dc": "Dc (m)",
            "V": "V entrada (m/s)",
            "Can": "Can velocity",
            "dpc": "dpc (µm)",
            "eta": "η global (%)",
            "dP": "ΔP (Pa)",
        }

        for c in columns:
            tree.heading(
                c,
                text=headings[c],
            )
            tree.column(
                c,
                width=140,
                anchor="center",
            )

        tree.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        self.comparison_tree = tree

        if self.comparison:
            self.fill_comparison_tree()

        if not self.comparison:
            self.run_comparison(
                self.compare_range.get()
            )

    def run_comparison(self, text):
        try:
            Dcs = [
                float(x.strip())
                for x in text.split(",")
                if x.strip()
            ]

            d = self.data

            results = []

            for Dc in Dcs:
                results.append(
                    calculate(
                        d["Q"],
                        d["T"],
                        d["P"],
                        d["rho_air"],
                        d["mu_air"],
                        d["rho_particle"],
                        Dc,
                        d["n"],
                        d["cyclone_type"],
                        d["psd_dp"],
                        d["weights"],
                        d["Ne"],
                        d["K"],
                    )
                )

            self.comparison = results
            self.fill_comparison_tree()

            self.plot_comparison()

        except Exception as exc:
            messagebox.showerror(
                "Comparación",
                str(exc),
            )

    def fill_comparison_tree(self):
        if not hasattr(self, "comparison_tree"):
            return

        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)

        for r in self.comparison:
            self.comparison_tree.insert(
                "",
                "end",
                values=(
                    f"{r.Dc:.3f}",
                    f"{r.V_in:.2f}",
                    f"{r.V_can:.2f}",
                    f"{r.dpc*1e6:.2f}",
                    f"{r.eta_global*100:.2f}",
                    f"{r.deltaP:.0f}",
                ),
            )

    def plot_comparison(self):
        if not self.comparison:
            return

        plt.figure(
            figsize=(9, 6)
        )

        plt.plot(
            [r.Dc for r in self.comparison],
            [r.eta_global * 100 for r in self.comparison],
            marker="o",
            linewidth=2,
        )

        plt.xlabel("Diámetro Dc (m)")
        plt.ylabel("Eficiencia global (%)")
        plt.title("Eficiencia global vs Dc")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --------------------------------------------------------
    # RECOMMENDATIONS PAGE
    # --------------------------------------------------------

    def build_recommendations_page(self):
        p = self.pages["recommendations"]

        self.page_header(
            p,
            "6",
            "Recomendaciones",
            "Interpretación automática y sugerencias de diseño.",
        )

        self.recommendation_content = tk.Frame(
            p,
            bg=BG,
        )
        self.recommendation_content.pack(
            fill="both",
            expand=True,
            padx=20,
        )

    def refresh_recommendations(self):
        for w in self.recommendation_content.winfo_children():
            w.destroy()

        if not self.result:
            return

        items = recommendations(
            self.result,
            self.data["material"],
            self.data["dpg_m"] * 1e6,
            self.data["sigma"],
            float(self.vmin.get()),
            float(self.vmax.get()),
            float(self.eta_target.get()),
            float(self.dp_max.get()),
        )

        mech = mechanical_design_recommendation(
            self.data["construction_material"],
            self.data["pressure_mode"],
            self.data["design_pressure_gauge_pa"],
            self.result.Dc,
        )

        structural = structural_screening(
            self.result,
            self.data,
            **self._get_structural_settings(),
        )

        banner = self.card(
            self.recommendation_content,
            "Recomendación general",
        )
        banner.pack(
            fill="x",
        )

        candidate = select_best(
            self.comparison,
            float(self.vmin.get()),
            float(self.vmax.get()),
            float(self.eta_target.get()) / 100,
            float(self.dp_max.get()),
        ) if self.comparison else None

        if candidate:
            message = (
                f"El mejor candidato dentro de los puntos comparados es "
                f"Dc={candidate.Dc:.3f} m, con "
                f"η={candidate.eta_global*100:.2f}%, "
                f"V={candidate.V_in:.2f} m/s y "
                f"ΔP={candidate.deltaP:.0f} Pa."
            )
        else:
            message = (
                "El punto actual debe revisarse según las recomendaciones "
                "individuales mostradas abajo. Use Comparación Dc para "
                "buscar un candidato que cumpla simultáneamente los límites."
            )

        tk.Label(
            banner,
            text=message,
            bg=WHITE,
            fg=NAVY,
            font=tk_font(11, weight="bold"),
            wraplength=1100,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        structural_box = tk.Frame(
            self.recommendation_content,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        structural_box.pack(
            fill="x",
            pady=7,
        )

        tk.Label(
            structural_box,
            text="PREDISEÑO ESTRUCTURAL",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(10, weight="bold"),
        ).pack(anchor="w")

        structural_text = (
            f"{structural['status']} | "
            f"t nominal = {structural['selected_nominal_mm']:.1f} mm | "
            f"anillos = {structural['rings']} | "
            f"utilización = {structural['utilization']*100:.1f}%\n"
            f"{structural['head_recommendation']}\n"
            f"{structural['ring_note']}"
        )

        tk.Label(
            structural_box,
            text=structural_text,
            bg=WHITE,
            fg=GREEN if structural["status"] == "CUMPLE SCREENING" else RED,
            wraplength=1000,
            justify="left",
            font=tk_font(9, weight="bold"),
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            structural_box,
            text=(
                "Es un screening preliminar de pandeo y resistencia. "
                "No equivale a una certificación de código."
            ),
            bg=WHITE,
            fg=ORANGE,
            wraplength=1000,
            justify="left",
            font=tk_font(8),
        ).pack(anchor="w", pady=(5, 0))

        # Recomendación de tubería para la entrada circular.
        pipe_box = tk.Frame(
            self.recommendation_content,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        pipe_box.pack(
            fill="x",
            pady=7,
        )

        tk.Label(
            pipe_box,
            text="TUBERÍA COMERCIAL PARA ENTRADA CIRCULAR",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(10, weight="bold"),
        ).pack(anchor="w")

        pipe_rec = pipe_candidates(
            self.result,
            self.data["construction_material"],
            float(self.vmin.get()),
            float(self.vmax.get()),
        )

        if pipe_rec["available"]:
            sel = pipe_rec["selected"]
            pipe_text = (
                f"Estado: {pipe_rec['status']} | "
                f"NPS {sel['nps']} / DN {sel['dn']} — Schedule {sel['schedule']}; "
                f"OD={sel['od_mm']:.1f} mm, t={sel['wall_mm']:.2f} mm, "
                f"ID={sel['id_mm']:.1f} mm, V={sel['velocity_m_s']:.2f} m/s.\n"
                f"Deq={pipe_rec['deq_m']*1000:.1f} mm | "
                f"V geométrica={pipe_rec['velocity_equivalent_m_s']:.2f} m/s.\n"
                f"{pipe_rec['selection_basis']} {pipe_rec['conflict_message']}\n"
                "Usar transición circular-tangencial y verificar pérdidas "
                "adicionales, soldadura, soportes y espesor por código."
            )
            pipe_color = GREEN if pipe_rec["status"] == "CUMPLE" else ORANGE
        else:
            pipe_text = pipe_rec["message"]
            pipe_color = ORANGE

        tk.Label(
            pipe_box,
            text=pipe_text,
            bg=WHITE,
            fg=pipe_color,
            wraplength=1000,
            justify="left",
            font=tk_font(9, weight="bold"),
        ).pack(anchor="w", pady=(4, 0))

        mech_box = tk.Frame(
            self.recommendation_content,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        mech_box.pack(
            fill="x",
            pady=7,
        )

        tk.Label(
            mech_box,
            text="CAD / CONSTRUCCIÓN",
            bg=WHITE,
            fg=NAVY,
            font=tk_font(10, weight="bold"),
        ).pack(anchor="w")

        mech_text = (
            f"Material: {mech['material']}  |  "
            f"Condición: {mech['severity']}  |  "
            f"Espesor preliminar: {mech['recommended_sheet_mm']:.1f} mm\n"
            f"Tapa: {mech['head_recommendation']}\n"
            f"Rigidización: {mech['stiffener_recommendation']}"
        )

        tk.Label(
            mech_box,
            text=mech_text,
            bg=WHITE,
            fg=MUTED,
            wraplength=1000,
            justify="left",
            font=tk_font(9),
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            mech_box,
            text=(
                "⚠ Este espesor es preliminar. El vacío debe verificarse "
                "por pandeo y no solamente por esfuerzo de membrana."
            ),
            bg=WHITE,
            fg=ORANGE,
            wraplength=1000,
            justify="left",
            font=tk_font(8, weight="bold"),
        ).pack(anchor="w", pady=(5, 0))

        for kind, title, message in items:
            colors = {
                "success": GREEN,
                "warning": ORANGE,
                "danger": RED,
                "info": NAVY,
                "tip": TEAL_DARK,
            }

            icons = {
                "success": "✓",
                "warning": "!",
                "danger": "×",
                "info": "i",
                "tip": "★",
            }

            box = tk.Frame(
                self.recommendation_content,
                bg=WHITE,
                highlightbackground=BORDER,
                highlightthickness=1,
                padx=12,
                pady=10,
            )
            box.pack(
                fill="x",
                pady=5,
            )

            tk.Label(
                box,
                text=icons[kind],
                bg=WHITE,
                fg=colors[kind],
                font=tk_font(17, weight="bold"),
                width=3,
            ).pack(
                side="left",
            )

            body = tk.Frame(
                box,
                bg=WHITE,
            )
            body.pack(
                side="left",
                fill="x",
                expand=True,
            )

            tk.Label(
                body,
                text=title,
                bg=WHITE,
                fg=colors[kind],
                font=tk_font(10, weight="bold"),
            ).pack(anchor="w")

            tk.Label(
                body,
                text=message,
                bg=WHITE,
                fg=MUTED,
                wraplength=1000,
                justify="left",
                font=tk_font(9),
            ).pack(anchor="w")

    # --------------------------------------------------------
    # REPORT PAGE
    # --------------------------------------------------------

    # --------------------------------------------------------
    # STRUCTURAL PAGE
    # --------------------------------------------------------

    def build_structural_page(self):
        p = self.pages["structural"]

        self.page_header(
            p,
            "7",
            "Diseño estructural",
            "Prediseño mecánico de carcasa, cono, rigidizadores y tapa.",
        )

        area = tk.Frame(
            p,
            bg=BG,
        )
        area.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5,
        )

        top = tk.Frame(
            area,
            bg=BG,
        )
        top.pack(
            fill="x",
        )

        settings = self.card(
            top,
            "Parámetros de prediseño estructural",
        )

        self.struct_corrosion, _ = self.field(
            settings,
            "Corrosion allowance",
            0,
            "1.0",
        )

        tk.Label(
            settings,
            text="mm",
            bg=WHITE,
            fg=MUTED,
            font=tk_font(8),
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(5, 0),
        )

        self.struct_weld, _ = self.field(
            settings,
            "Eficiencia soldadura",
            1,
            "0.85",
        )

        self.struct_fs, _ = self.field(
            settings,
            "Factor de seguridad",
            2,
            "2.0",
        )

        self.struct_rings, _ = self.field(
            settings,
            "Máx. anillos a evaluar",
            3,
            "4",
        )

        tk.Label(
            settings,
            text=(
                "El programa evalúa espesores comerciales y busca una "
                "combinación de lámina + anillos que resista el vacío "
                "de diseño en un screening preliminar."
            ),
            bg=TEAL_LIGHT,
            fg=TEXT,
            wraplength=420,
            justify="left",
            padx=8,
            pady=8,
            font=tk_font(8),
        ).grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(10, 0),
        )

        ref = self.card(
            top,
            "Referencia y alcance",
        )

        tk.Label(
            ref,
            text=(
                "Referencia conceptual: ASME BPVC Section VIII Division 1, "
                "especialmente diseño de cuerpos/cabezales bajo presión "
                "externa y rigidizadores. Esta pantalla NO implementa el "
                "procedimiento normativo completo de UG-28/UG-29 ni declara "
                "cumplimiento ASME."
            ),
            bg=WHITE,
            fg=MUTED,
            wraplength=430,
            justify="left",
            font=tk_font(9),
        ).pack(
            anchor="w",
            pady=5,
        )

        tk.Label(
            ref,
            text=(
                "El objetivo es seleccionar un concepto CAD razonable, "
                "identificar si el vacío domina y orientar espesor, anillos "
                "y tipo de tapa antes de una verificación mecánica formal."
            ),
            bg=WHITE,
            fg=TEXT,
            wraplength=430,
            justify="left",
            font=tk_font(9, weight="bold"),
        ).pack(
            anchor="w",
            pady=5,
        )

        tk.Button(
            ref,
            text="▶  ACTUALIZAR PREDISEÑO ESTRUCTURAL",
            command=self.refresh_structural,
            bg=TEAL,
            fg=WHITE,
            activebackground=TEAL_DARK,
            activeforeground=WHITE,
            bd=0,
            padx=12,
            pady=9,
            font=tk_font(9, weight="bold"),
        ).pack(
            anchor="w",
            pady=(12, 4),
        )

        self.structural_content = tk.Frame(
            area,
            bg=BG,
        )
        self.structural_content.pack(
            fill="both",
            expand=True,
            pady=(8, 0),
        )

    def _get_structural_settings(self):
        return {
            "corrosion_mm": float(self.struct_corrosion.get()),
            "weld_eff": float(self.struct_weld.get()),
            "FS": float(self.struct_fs.get()),
            "max_rings": int(float(self.struct_rings.get())),
        }

    def refresh_structural(self):
        for w in self.structural_content.winfo_children():
            w.destroy()

        if not self.result or not self.data:
            return

        try:
            settings = self._get_structural_settings()
            self.structural_result = structural_screening(
                self.result,
                self.data,
                **settings,
            )
        except Exception as exc:
            tk.Label(
                self.structural_content,
                text=f"Error en prediseño estructural: {exc}",
                bg=WHITE,
                fg=RED,
                font=tk_font(10, weight="bold"),
                padx=15,
                pady=15,
            ).pack(
                fill="x",
            )
            return

        s = self.structural_result

        # Summary cards
        summary = tk.Frame(
            self.structural_content,
            bg=BG,
        )
        summary.pack(
            fill="x",
        )

        cards = [
            (
                "Vacío / presión externa",
                f"{s['P_external_kPa']:.2f} kPa",
                ORANGE,
            ),
            (
                "Espesor nominal",
                f"{s['selected_nominal_mm']:.1f} mm",
                TEAL_DARK,
            ),
            (
                "Anillos",
                str(s["rings"]),
                NAVY,
            ),
            (
                "Utilización",
                f"{s['utilization']*100:.1f} %",
                GREEN if s["utilization"] <= 1 else RED,
            ),
        ]

        for i, (label, value, color) in enumerate(cards):
            box = tk.Frame(
                summary,
                bg=WHITE,
                highlightbackground=BORDER,
                highlightthickness=1,
                padx=12,
                pady=10,
            )
            box.grid(
                row=0,
                column=i,
                sticky="nsew",
                padx=4,
            )
            tk.Label(
                box,
                text=label,
                bg=WHITE,
                fg=MUTED,
                font=tk_font(8),
            ).pack(anchor="w")
            tk.Label(
                box,
                text=value,
                bg=WHITE,
                fg=color,
                font=tk_font(16, weight="bold"),
            ).pack(anchor="w", pady=(2, 0))

        for i in range(4):
            summary.columnconfigure(i, weight=1)

        # Main tables
        body = tk.Frame(
            self.structural_content,
            bg=BG,
        )
        body.pack(
            fill="both",
            expand=True,
            pady=8,
        )

        left = self.card(
            body,
            "Verificación de carcasa y cono",
        )

        rows = [
            ("Material", s["material"]),
            ("E", f"{s['E_GPa']:.1f} GPa"),
            ("ν", f"{s['nu']:.3f}"),
            ("Límite elástico de referencia", f"{s['Sy_MPa']:.0f} MPa"),
            ("Esfuerzo permisible de screening", f"{s['S_allow_MPa']:.1f} MPa"),
            ("Espesor requerido por presión interna", f"{max(s['shell_t_internal_mm'], s['cone_t_internal_mm']):.2f} mm"),
            ("Espesor nominal seleccionado", f"{s['selected_nominal_mm']:.1f} mm"),
            ("Espesor neto", f"{s['selected_net_mm']:.1f} mm"),
            ("Presión admisible cilindro", f"{s['p_allow_cyl_kPa']:.2f} kPa"),
            ("Presión admisible cono", f"{s['p_allow_cone_kPa']:.2f} kPa"),
            ("Presión admisible gobernante", f"{s['p_allow_structural_kPa']:.2f} kPa"),
            ("Estado", s["status"]),
        ]

        for i, (label, value) in enumerate(rows):
            tk.Label(
                left,
                text=label,
                bg=WHITE,
                fg=MUTED,
                font=tk_font(8, weight="bold"),
            ).grid(
                row=i,
                column=0,
                sticky="w",
                pady=4,
            )
            tk.Label(
                left,
                text=value,
                bg=WHITE,
                fg=GREEN if "CUMPLE" in value else TEXT,
                font=("Segoe UI", 9, "bold" if label == "Estado" else "normal"),
            ).grid(
                row=i,
                column=1,
                sticky="w",
                padx=(12, 0),
                pady=4,
            )

        right = self.card(
            body,
            "Recomendación de tapa y rigidización",
        )

        tk.Label(
            right,
            text=s["head_recommendation"],
            bg=TEAL_LIGHT,
            fg=NAVY,
            wraplength=470,
            justify="left",
            padx=10,
            pady=10,
            font=tk_font(10, weight="bold"),
        ).pack(
            fill="x",
            pady=5,
        )

        tk.Label(
            right,
            text=(
                f"Pantalla de tapa plana por flexión: "
                f"{s['flat_head_net_mm']:.2f} mm netos; "
                f"{s['flat_head_nominal_mm']:.1f} mm nominales."
            ),
            bg=WHITE,
            fg=TEXT,
            wraplength=470,
            justify="left",
            font=tk_font(9),
        ).pack(
            anchor="w",
            pady=7,
        )

        tk.Label(
            right,
            text=s["ring_note"],
            bg=WHITE,
            fg=NAVY,
            wraplength=470,
            justify="left",
            font=tk_font(9, weight="bold"),
        ).pack(
            anchor="w",
            pady=7,
        )

        tk.Label(
            right,
            text=(
                "Criterio de selección: se prueban espesores comerciales "
                "de 1.5 a 16 mm y de 0 a N anillos. Se selecciona primero "
                "el menor espesor comercial que cumple el screening."
            ),
            bg=WHITE,
            fg=MUTED,
            wraplength=470,
            justify="left",
            font=tk_font(8),
        ).pack(
            anchor="w",
            pady=7,
        )

        warning = tk.Frame(
            self.structural_content,
            bg="#FFF7E8",
            highlightbackground="#F0C36A",
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        warning.pack(
            fill="x",
        )

        tk.Label(
            warning,
            text="⚠ LIMITACIÓN DEL CÁLCULO",
            bg="#FFF7E8",
            fg=ORANGE,
            font=tk_font(9, weight="bold"),
        ).pack(anchor="w")

        tk.Label(
            warning,
            text=s["screening_note"],
            bg="#FFF7E8",
            fg=TEXT,
            wraplength=1100,
            justify="left",
            font=tk_font(8),
        ).pack(
            anchor="w",
            pady=(4, 0),
        )

    def build_report_page(self):
        p = self.pages["report"]

        self.page_header(
            p,
            "8",
            "Informe",
            "Revise y exporte la memoria de cálculo.",
        )

        self.report_content = tk.Frame(
            p,
            bg=BG,
        )
        self.report_content.pack(
            fill="both",
            expand=True,
            padx=20,
        )

    def refresh_report(self):
        for w in self.report_content.winfo_children():
            w.destroy()

        if not self.result:
            return

        card = self.card(
            self.report_content,
            "Memoria de cálculo",
        )
        card.pack(
            fill="both",
            expand=True,
        )

        status = tk.Frame(card, bg=TEAL_LIGHT)
        status.pack(fill="x", pady=(0, 8))

        tk.Label(
            status,
            text=(
                "MEMORIA ACTUALIZADA — incluye datos de entrada, "
                "ecuaciones de prediseño, resultados, CAD y recomendaciones."
            ),
            bg=TEAL_LIGHT,
            fg=TEAL_DARK,
            font=tk_font(8, weight="bold"),
            padx=10,
            pady=6,
            anchor="w",
        ).pack(fill="x")

        text_frame = tk.Frame(card, bg="#F8FAFD")
        text_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
        )
        scrollbar.pack(side="right", fill="y")

        text = tk.Text(
            text_frame,
            font=("Consolas", 9),
            bg="#F8FAFD",
            fg=TEXT,
            relief="flat",
            wrap="word",
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=8,
        )
        text.pack(
            side="left",
            fill="both",
            expand=True,
        )
        scrollbar.configure(command=text.yview)

        try:
            report = self.generate_report_text()
        except Exception as exc:
            report = (
                "NO FUE POSIBLE GENERAR LA MEMORIA DE CÁLCULO.\n\n"
                f"Detalle técnico: {exc}\n\n"
                "Verifique los datos de entrada y vuelva a presionar CALCULAR."
            )

        text.insert("1.0", report)
        text.configure(state="disabled")
        text.see("1.0")

        buttons = tk.Frame(
            card,
            bg=WHITE,
        )
        buttons.pack(
            fill="x",
            pady=(10, 0),
        )

        tk.Button(
            buttons,
            text="↻ Actualizar memoria",
            command=self.refresh_report,
            bg=TEAL_LIGHT,
            fg=TEAL_DARK,
            bd=0,
            padx=12,
            pady=8,
            font=tk_font(9, weight="bold"),
        ).pack(
            side="left",
            padx=(0, 8),
        )

        tk.Button(
            buttons,
            text="Guardar informe TXT",
            command=self.export_report,
            bg=TEAL,
            fg=WHITE,
            bd=0,
            padx=12,
            pady=8,
            font=tk_font(9, weight="bold"),
        ).pack(
            side="left",
        )

        tk.Button(
            buttons,
            text="Exportar PDF para CAD",
            command=self.export_pdf,
            bg=NAVY,
            fg=WHITE,
            bd=0,
            padx=12,
            pady=8,
            font=tk_font(9, weight="bold"),
        ).pack(
            side="left",
            padx=8,
        )

        tk.Button(
            buttons,
            text="Guardar resultados CSV",
            command=self.export_csv,
            bg=NAVY_LIGHT,
            fg=WHITE,
            bd=0,
            padx=12,
            pady=8,
            font=tk_font(9, weight="bold"),
        ).pack(
            side="left",
            padx=8,
        )

    def generate_theory_text(self):
        """Explicación técnica de las ecuaciones implementadas."""
        return """BASE TEÓRICA DE LOS CÁLCULOS
============================

1. GEOMETRÍA STAIRMAND
Las dimensiones se expresan como fracciones de Dc para conservar similitud geométrica.
Modelo implementado: a=0.50Dc, b=0.20Dc, De=0.50Dc, S=0.50De, h=1.50Dc, H=4.00Dc, B=0.375Dc.
Referencia principal: Stairmand (1951) [R1]; fundamento moderno: Hoffmann y Stein (2002) [R7].

2. CONTINUIDAD Y VELOCIDAD DE ENTRADA
Qc = Qtotal/N
Ae = a*b
Vi = Qc/Ae
Qc reparte el caudal entre ciclones en paralelo. Ae es el área de la entrada tangencial y Vi se obtiene de continuidad para flujo estacionario. Una mayor velocidad suele aumentar la eficiencia, pero también la pérdida de presión [R3, R6].

3. CAN VELOCITY
Ac = pi*Dc²/4
Vcan = Qc/Ac
Es una velocidad media de referencia sobre la sección del cuerpo; no representa el campo tridimensional real.

4. REYNOLDS
Re = rho_g*Vi*Dc/mu
Relaciona fuerzas inerciales y viscosas y sirve para caracterizar el régimen del flujo [R5, R7].

5. DIÁMETRO DE CORTE DE LAPPLE
dpc = sqrt(9*mu*b/[2*pi*Ne*Vi*(rho_p-rho_g)])
El diámetro de corte representa aproximadamente el tamaño de partícula con 50 % de eficiencia en este modelo. La expresión clásica aparece en el método de Lapple y en EPA/APTI [R2, R5]. El código actual aproxima rho_p-rho_g por rho_p cuando la densidad del sólido es mucho mayor que la del aire.

6. EFICIENCIA FRACCIONAL
eta(dp) = 1/[1+(dpc/dp)²]
Por construcción eta=0.5 cuando dp=dpc. Las partículas grandes respecto a dpc presentan mayor probabilidad de captura. Es una correlación de prediseño, no una solución CFD [R2, R5].

7. EFICIENCIA GLOBAL
eta_global = SUM[eta(dp_i)*w_i]
La eficiencia de cada tamaño se pondera por la fracción de masa de la PSD. Esto evita representar todo el material con un único diámetro [R5].

8. PSD LOG-NORMAL
Se genera una distribución log-normal alrededor de dpg con sigma_g y se normaliza para SUM(w_i)=1. Es útil para prediseño; para diseño final se recomienda introducir la PSD medida.

9. PÉRDIDA DE PRESIÓN
DeltaP = K*rho_g*Vi²/2
El término rho_g*Vi²/2 es presión dinámica y K agrupa pérdidas. K depende de geometría y operación; debe validarse para el ciclón real [R3, R4, R6].

10. TIEMPO DE RESIDENCIA APROXIMADO
tr = Ne*pi*Dc/Vi
Es una escala cinemática aproximada asociada a Ne vueltas y no sustituye un campo de velocidad real o CFD.

11. DIÁMETRO CIRCULAR EQUIVALENTE
Deq = sqrt(4*Ae/pi)
Con esta relación, pi*Deq²/4=Ae. Se utiliza para seleccionar preliminarmente una tubería circular que conserve el área de entrada. La conexión final debe utilizar una transición circular-tangencial.

12. GEOMETRÍA DEL CONO
Hcono=H-h
Lc=sqrt[Hcono²+((Dc-B)/2)²]
alpha=atan[((Dc-B)/2)/Hcono]
Son relaciones geométricas para generar el modelo CAD.

13. SCREENING ESTRUCTURAL
La presión interna se revisa mediante equilibrio de membrana. La presión externa se evalúa mediante un modelo elástico simplificado de pandeo con reducción por imperfecciones y longitud libre aproximada. La tapa plana se compara mediante una relación simplificada de flexión. Estos cálculos NO implementan literalmente ASME UG-28/UG-29 y no constituyen certificación [R8, R9].

14. ALCANCE
Las ecuaciones de eficiencia, dpc y DeltaP son correlaciones/modelos de prediseño. El resultado debe validarse con PSD real, carga de sólidos, temperatura, humedad/cohesión, pérdidas reales y, cuando sea necesario, pruebas o CFD.
"""

    def generate_report_text(self):
        r = self.result
        d = self.data
        g = r.geometry

        items = recommendations(
            r,
            d["material"],
            d["dpg_m"] * 1e6,
            d["sigma"],
            float(self.vmin.get()),
            float(self.vmax.get()),
            float(self.eta_target.get()),
            float(self.dp_max.get()),
        )

        mech = mechanical_design_recommendation(
            d["construction_material"],
            d["pressure_mode"],
            d["design_pressure_gauge_pa"],
            r.Dc,
        )

        structural = structural_screening(
            r,
            d,
            **self._get_structural_settings(),
        )

        lines = [
            "SYCSAtech - CALCULADOR DE CICLONES V18",
            "=" * 72,
            "",
            "DATOS DE ENTRADA",
            "-" * 72,
            "Propiedades de aire: tabla IAEA, aire seco, P=0.0981 MPa; "
            "interpolación en T y corrección de densidad por P.",
            "Fuente: IAEA, Thermophysical Properties of Materials, Table 3.1.",
            f"Material: {d['material']}",
            f"Caudal total: {d['Q']:.8f} m³/s",
            f"Temperatura: {d['T']:.2f} K",
            f"Presión absoluta: {d['P']:.2f} Pa",
            f"Densidad aire: {d['rho_air']:.8f} kg/m³",
            f"Viscosidad aire: {d['mu_air']:.8e} Pa·s",
            f"Densidad partícula: {d['rho_particle']:.3f} kg/m³",
            f"dpg: {d['dpg_m']*1e6:.3f} µm",
            f"σg: {d['sigma']:.3f}",
            f"Fuente de PSD: {d['psd_source']}",
            "",
            "DISEÑO",
            "-" * 72,
            f"Geometría: {g.name}",
            f"Dc: {r.Dc:.6f} m",
            f"a: {g.a:.6f} m",
            f"b: {g.b:.6f} m",
            f"De: {g.De:.6f} m",
            f"S: {g.S:.6f} m",
            f"h: {g.h:.6f} m",
            f"H: {g.H:.6f} m",
            f"B: {g.B:.6f} m",
            f"Ciclones en paralelo: {r.n_cyclones}",
            "",
            "BASE TEÓRICA — ECUACIONES Y CRITERIO",
            "-" * 72,
            *self.generate_theory_text().splitlines(),
            "",
            "MEMORIA DE CÁLCULO — ECUACIONES Y CRITERIO",
            "-" * 72,
            "1) Conversión de unidades: todas las entradas se convierten a SI antes del cálculo.",
            "2) Propiedades del aire: interpolación de tabla y corrección de densidad por P [R5].",
            "3) Geometría Stairmand: relaciones adimensionales basadas en Dc [R1, R7].",
            "4) Área de entrada: Ae = a·b, por definición geométrica.",
            "5) Caudal por ciclón: Qc = Qtotal/N, por continuidad en paralelo.",
            "6) Velocidad de entrada: Vi = Qc/Ae, por continuidad [R3, R7].",
            "7) Can velocity: Vcan = Qc/(pi·Dc²/4), velocidad media de referencia.",
            "8) Reynolds: Re = rho·Vi·Dc/mu, número adimensional [R5, R7].",
            "9) Diámetro de corte: modelo de Lapple [R2, R5].",
            "10) Eficiencia fraccional: eta = 1/[1+(dpc/dp)²], correlación de prediseño [R2, R5].",
            "11) Eficiencia global: eta_global = sum(eta_i·w_i), integración discreta de PSD [R5].",
            "12) Pérdida de presión: ΔP = K·rho·Vi²/2 [R3, R4, R6].",
            "13) Tiempo de residencia: tr ≈ Ne·pi·Dc/Vi, escala cinemática aproximada.",
            "14) Entrada circular: Deq = sqrt(4·Ae/pi), conservación de área para CAD.",
            "15) Prediseño estructural: membrana y screening de pandeo; no sustituye ASME [R8, R9].",
            "",
            "ESTATUS DE LAS ECUACIONES",
            "-" * 72,
            "Las ecuaciones de proceso son correlaciones/modelos de prediseño. "
            "No sustituyen CFD, pruebas ni validación experimental. La selección "
            "final debe considerar concentración de sólidos, humedad, cohesión, "
            "temperatura, desgaste, fugas, descarga de sólidos y pérdidas reales.",
            "",
            "RESULTADOS",
            "-" * 72,
            f"Caudal por ciclón: {r.Q_cyclone:.8f} m³/s",
            f"Velocidad entrada: {r.V_in:.5f} m/s",
            f"Can velocity: {r.V_can:.5f} m/s",
            f"Reynolds: {r.Reynolds:.6e}",
            f"Diámetro de corte: {r.dpc*1e6:.5f} µm",
            f"Eficiencia global: {r.eta_global*100:.5f} %",
            f"Pérdida de presión: {r.deltaP:.3f} Pa",
            f"Tiempo residencia aprox.: {r.residence_time:.6f} s",
            "",
            "DATOS DERIVADOS PARA CAD",
            "-" * 72,
            f"Altura del cono H-h: {max(g.H-g.h,0):.6f} m",
            f"Ángulo semicono: {math.degrees(math.atan2((g.Dc-g.B)/2, max(g.H-g.h,1e-12))):.3f}°",
            f"Ángulo incluido del cono: {2*math.degrees(math.atan2((g.Dc-g.B)/2, max(g.H-g.h,1e-12))):.3f}°",
            f"Área de entrada Ae: {r.area_inlet:.8f} m²",
            f"Área entrada rectangular a·b: {g.a*g.b:.8f} m²",
            f"Diámetro circular equivalente Deq: {inlet_pipe_recommendation(r)['deq_m']*1000:.2f} mm",
            f"Velocidad con área equivalente: {inlet_pipe_recommendation(r)['velocity_m_s']:.3f} m/s",
            "Recomendación de entrada: tubería calibrada o Schedule 10/10S "
            "con transición circular-tangencial.",
            f"Área cilíndrica Ac: {math.pi*r.Dc**2/4:.8f} m²",
            "",
            "RECOMENDACIONES",
            "-" * 72,
            f"Material de construcción: {mech['material']}",
            f"Condición mecánica: {mech['severity']}",
            f"Presión/vacío de diseño: {mech['pressure_kpa']:.3f} kPa",
            f"Espesor preliminar de especificación: {mech['recommended_sheet_mm']:.1f} mm",
            f"Recomendación de tapa: {mech['head_recommendation']}",
            f"Rigidizadores: {mech['stiffener_recommendation']}",
            f"Nota de material: {mech['material_note']}",
            f"ADVERTENCIA: {mech['caution']}",
            "",
            "PREDISEÑO ESTRUCTURAL — SCREENING",
            "-" * 72,
            f"Presión externa de diseño: {structural['P_external_kPa']:.3f} kPa",
            f"Espesor nominal seleccionado: {structural['selected_nominal_mm']:.1f} mm",
            f"Espesor neto: {structural['selected_net_mm']:.1f} mm",
            f"Anillos rigidizadores: {structural['rings']}",
            f"Presión admisible cilindro: {structural['p_allow_cyl_kPa']:.3f} kPa",
            f"Presión admisible cono: {structural['p_allow_cone_kPa']:.3f} kPa",
            f"Presión admisible gobernante: {structural['p_allow_structural_kPa']:.3f} kPa",
            f"Utilización estructural: {structural['utilization']*100:.2f} %",
            f"Tapa: {structural['head_recommendation']}",
            f"Pantalla tapa plana: {structural['flat_head_nominal_mm']:.1f} mm nominal",
            f"Estado: {structural['status']}",
            f"NOTA: {structural['screening_note']}",
            "",
            "BASE TEÓRICA Y REFERENCIAS",
            "-" * 72,
            "[R1] U.S. EPA — Air Pollution Control Technology Fact Sheet: Cyclones.",
            "[R2] U.S. EPA — APTI Course 413: Control of Particulate Emissions.",
            "[R3] Perry's Chemical Engineers' Handbook, 7th ed., Gas-Solid Separations.",
            "[R4] ASME BPVC Section VIII Division 1.",
            "[R5] ASME BPVC Section II Part D.",
            "[R6] Bird, Stewart & Lightfoot — Transport Phenomena.",
            "[R7] White — Fluid Mechanics.",
            "[R8] ASME B36.10/B36.10M — tubería de acero al carbón.",
            "[R9] ASME B36.19/B36.19M — tubería de acero inoxidable.",
            "Las referencias respaldan la base teórica; el screening estructural "
            "no constituye cumplimiento ASME.",
        ]

        for kind, title, message in items:
            lines.append(
                f"[{kind.upper()}] {title}: {message}"
            )

        lines.extend([
            "",
            "NOTA:",
            "Los resultados son de prediseño y deben validarse "
            "con la geometría real, PSD medida y condiciones "
            "de operación antes de fabricar o especificar el equipo.",
        ])

        return "\n".join(lines)

    # --------------------------------------------------------
    # DATA / CALCULATION
    # --------------------------------------------------------

    # --------------------------------------------------------
    # PSD MEASURED TABLE
    # --------------------------------------------------------

    def update_psd_mode_state(self):
        """Actualiza el estado visual de la opción de PSD seleccionada."""
        mode = self.psd_mode.get()

        if mode == "table":
            self.psd_table_button.configure(
                bg=TEAL_LIGHT,
                fg=TEAL_DARK,
            )
        else:
            self.psd_table_button.configure(
                bg=WHITE,
                fg=NAVY,
            )

    def open_psd_table(self):
        """Abre una ventana donde el usuario introduce la PSD medida."""
        win = tk.Toplevel(self.root)
        win.title("SYCSAtech - Tabla de granulometría")
        win.geometry("620x700")
        win.minsize(560, 600)
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="GRANULOMETRÍA MEDIDA",
            bg=NAVY,
            fg=WHITE,
            font=tk_font(14, weight="bold"),
            pady=10,
        ).pack(fill="x")

        tk.Label(
            win,
            text=(
                "Introduzca la distribución granulométrica del material.\\n"
                "Use diámetro de partícula en µm y porcentaje en masa (%).\\n"
                "Los porcentajes deben sumar 100 %. Si no suman 100 %, "
                "puede utilizar NORMALIZAR."
            ),
            bg=BG,
            fg=MUTED,
            justify="left",
            font=tk_font(9),
            padx=15,
            pady=10,
        ).pack(fill="x")

        table_container = tk.Frame(
            win,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        table_container.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=5,
        )

        header = tk.Frame(
            table_container,
            bg=NAVY_LIGHT,
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text="No.",
            width=6,
            bg=NAVY_LIGHT,
            fg=WHITE,
            font=tk_font(9, weight="bold"),
        ).grid(row=0, column=0, padx=2, pady=6)

        tk.Label(
            header,
            text="Diámetro de partícula (µm)",
            width=27,
            bg=NAVY_LIGHT,
            fg=WHITE,
            font=tk_font(9, weight="bold"),
        ).grid(row=0, column=1, padx=2, pady=6)

        tk.Label(
            header,
            text="% masa",
            width=14,
            bg=NAVY_LIGHT,
            fg=WHITE,
            font=tk_font(9, weight="bold"),
        ).grid(row=0, column=2, padx=2, pady=6)

        canvas = tk.Canvas(
            table_container,
            bg=WHITE,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            table_container,
            orient="vertical",
            command=canvas.yview,
        )
        rows_frame = tk.Frame(
            canvas,
            bg=WHITE,
        )

        rows_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )

        canvas.create_window(
            (0, 0),
            window=rows_frame,
            anchor="nw",
        )
        canvas.configure(
            yscrollcommand=scrollbar.set,
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )
        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.psd_table_entries = []

        # Load existing PSD values first.
        existing = list(self.psd_table_data)

        # Give the user 20 editable rows.
        for i in range(20):
            if i < len(existing):
                d_value, p_value = existing[i]
                d_value = f"{d_value:g}"
                p_value = f"{p_value:g}"
            else:
                d_value = ""
                p_value = ""

            tk.Label(
                rows_frame,
                text=str(i + 1),
                width=6,
                bg=WHITE,
                fg=MUTED,
                font=tk_font(9),
            ).grid(
                row=i,
                column=0,
                padx=2,
                pady=3,
            )

            d_entry = ttk.Entry(
                rows_frame,
                width=30,
            )
            d_entry.grid(
                row=i,
                column=1,
                padx=2,
                pady=3,
            )
            if d_value:
                d_entry.insert(0, d_value)

            p_entry = ttk.Entry(
                rows_frame,
                width=17,
            )
            p_entry.grid(
                row=i,
                column=2,
                padx=2,
                pady=3,
            )
            if p_value:
                p_entry.insert(0, p_value)

            self.psd_table_entries.append(
                (d_entry, p_entry)
            )

        sum_var = tk.StringVar(
            value="Suma: 0.00 %"
        )

        def read_rows():
            data = []

            for d_entry, p_entry in self.psd_table_entries:
                d_txt = d_entry.get().strip()
                p_txt = p_entry.get().strip()

                if not d_txt and not p_txt:
                    continue

                if not d_txt or not p_txt:
                    raise ValueError(
                        "Cada fila utilizada debe tener diámetro y % masa."
                    )

                d = float(d_txt)
                pct = float(p_txt)

                if d <= 0:
                    raise ValueError(
                        "Los diámetros deben ser mayores que cero."
                    )

                if pct < 0:
                    raise ValueError(
                        "Los porcentajes no pueden ser negativos."
                    )

                data.append((d, pct))

            if not data:
                raise ValueError(
                    "Introduzca al menos un punto de granulometría."
                )

            data.sort(key=lambda x: x[0])
            return data

        def update_sum(event=None):
            try:
                data = read_rows()
                total = sum(p for _, p in data)
                sum_var.set(
                    f"Suma: {total:.2f} %"
                )
            except Exception:
                sum_var.set(
                    "Suma: —"
                )

        for d_entry, p_entry in self.psd_table_entries:
            d_entry.bind(
                "<KeyRelease>",
                update_sum,
            )
            p_entry.bind(
                "<KeyRelease>",
                update_sum,
            )

        bottom = tk.Frame(
            win,
            bg=BG,
            padx=15,
            pady=10,
        )
        bottom.pack(
            fill="x",
        )

        tk.Label(
            bottom,
            textvariable=sum_var,
            bg=BG,
            fg=NAVY,
            font=tk_font(10, weight="bold"),
        ).pack(
            side="left",
        )

        def normalize():
            try:
                data = read_rows()
                total = sum(p for _, p in data)

                if total <= 0:
                    raise ValueError(
                        "La suma de los porcentajes debe ser mayor que cero."
                    )

                for d_entry, p_entry in self.psd_table_entries:
                    p_txt = p_entry.get().strip()
                    if p_txt:
                        pct = float(p_txt)
                        p_entry.delete(0, "end")
                        p_entry.insert(
                            0,
                            f"{pct / total * 100:.4f}"
                        )

                update_sum()

            except Exception as exc:
                messagebox.showerror(
                    "Normalizar PSD",
                    str(exc),
                    parent=win,
                )

        def example():
            example_data = [
                (10, 2.0),
                (20, 5.0),
                (30, 8.0),
                (50, 14.0),
                (75, 18.0),
                (100, 20.0),
                (150, 15.0),
                (200, 10.0),
                (300, 5.0),
                (500, 3.0),
            ]

            for i, (d, pct) in enumerate(example_data):
                d_entry, p_entry = self.psd_table_entries[i]
                d_entry.delete(0, "end")
                d_entry.insert(0, str(d))
                p_entry.delete(0, "end")
                p_entry.insert(0, str(pct))

            for i in range(len(example_data), len(self.psd_table_entries)):
                d_entry, p_entry = self.psd_table_entries[i]
                d_entry.delete(0, "end")
                p_entry.delete(0, "end")

            update_sum()

        def clear_table():
            for d_entry, p_entry in self.psd_table_entries:
                d_entry.delete(0, "end")
                p_entry.delete(0, "end")
            sum_var.set("Suma: 0.00 %")

        def apply_table():
            try:
                data = read_rows()
                total = sum(p for _, p in data)

                if total <= 0:
                    raise ValueError(
                        "La suma de los porcentajes debe ser mayor que cero."
                    )

                if abs(total - 100.0) > 0.05:
                    answer = messagebox.askyesno(
                        "PSD no normalizada",
                        (
                            f"La suma actual es {total:.2f} %.\\n\\n"
                            "¿Desea normalizar automáticamente la distribución "
                            "para que sume 100 %?"
                        ),
                        parent=win,
                    )

                    if not answer:
                        return

                    normalized = [
                        (d, p / total * 100.0)
                        for d, p in data
                    ]
                    data = normalized

                self.psd_table_data = data
                self.psd_mode.set("table")
                self.psd_table_status.set(
                    f"PSD medida: {len(data)} puntos | "
                    f"Suma = {sum(p for _, p in data):.2f} %"
                )
                self.update_psd_mode_state()
                win.destroy()

            except Exception as exc:
                messagebox.showerror(
                    "Tabla de granulometría",
                    str(exc),
                    parent=win,
                )

        tk.Button(
            bottom,
            text="Ejemplo",
            command=example,
            bg=WHITE,
            fg=NAVY,
            bd=1,
            relief="solid",
            padx=10,
        ).pack(
            side="right",
            padx=4,
        )

        tk.Button(
            bottom,
            text="Normalizar",
            command=normalize,
            bg=WHITE,
            fg=NAVY,
            bd=1,
            relief="solid",
            padx=10,
        ).pack(
            side="right",
            padx=4,
        )

        tk.Button(
            bottom,
            text="Limpiar",
            command=clear_table,
            bg=WHITE,
            fg=RED,
            bd=1,
            relief="solid",
            padx=10,
        ).pack(
            side="right",
            padx=4,
        )

        tk.Button(
            bottom,
            text="CANCELAR",
            command=win.destroy,
            bg=WHITE,
            fg=NAVY,
            bd=1,
            relief="solid",
            padx=12,
        ).pack(
            side="right",
            padx=4,
        )

        tk.Button(
            bottom,
            text="APLICAR PSD",
            command=apply_table,
            bg=TEAL,
            fg=WHITE,
            activebackground=TEAL_DARK,
            activeforeground=WHITE,
            bd=0,
            padx=14,
            pady=7,
            font=tk_font(9, weight="bold"),
        ).pack(
            side="right",
            padx=4,
        )

        update_sum()

    def get_table_psd(self):
        """Convierte la tabla PSD medida en dp (m) y pesos de masa."""
        if not self.psd_table_data:
            raise ValueError(
                "Seleccione 'PSD medida — introducir tabla' y cargue "
                "al menos un punto de granulometría."
            )

        data = sorted(
            self.psd_table_data,
            key=lambda x: x[0],
        )

        total = sum(
            pct for _, pct in data
        )

        if total <= 0:
            raise ValueError(
                "La suma de la PSD debe ser mayor que cero."
            )

        dp = np.array(
            [diameter * 1e-6 for diameter, _ in data],
            dtype=float,
        )

        weights = np.array(
            [pct / total for _, pct in data],
            dtype=float,
        )

        return dp, weights

    def update_material(self, event=None):
        name = self.material.get()
        d = MATERIALES[name]

        self.rho_particle.delete(0, "end")
        self.rho_particle.insert(0, str(d["rho"]))

        self.dpg.delete(0, "end")
        self.dpg.insert(0, str(d["dpg"]))

        self.sigma.delete(0, "end")
        self.sigma.insert(0, str(d["sigma"]))

        self.dpg_unit.set("µm")

    def read_inputs(self):
        Q = convert(
            self.q.get(),
            self.q_unit.get(),
            FLOW,
        )

        T = float(self.temp.get())
        T_K = (
            T + 273.15
            if self.temp_unit.get() == "°C"
            else T
        )

        P = convert(
            self.press.get(),
            self.press_unit.get(),
            PRESSURE,
        )

        # Las propiedades del aire se determinan automáticamente a partir
        # de la temperatura y la presión absoluta de proceso. El usuario
        # no necesita introducir ρ ni μ manualmente.
        rho_air, mu_air = air_properties(T_K, P)

        self.rho_air_display.set(f"{rho_air:.4f} kg/m³")
        self.mu_air_display.set(f"{mu_air:.6e} Pa·s")

        rho_particle = float(
            self.rho_particle.get()
        )

        dpg_m = convert(
            self.dpg.get(),
            self.dpg_unit.get(),
            LENGTH,
        )

        sigma = float(
            self.sigma.get()
        )

        if self.psd_mode.get() == "lognormal":
            psd_dp, weights = lognormal_psd(
                dpg_m * 1e6,
                sigma,
            )
            psd_source = "Distribución log-normal"
        elif self.psd_mode.get() == "table":
            psd_dp, weights = self.get_table_psd()
            psd_source = "PSD medida introducida por tabla"

            # Para una PSD medida, calculamos dpg y sigma equivalentes
            # únicamente como indicadores descriptivos.
            ln_dp = np.log(psd_dp)
            ln_mean = float(np.sum(weights * ln_dp))
            ln_sigma = float(
                np.sqrt(
                    np.sum(weights * (ln_dp - ln_mean) ** 2)
                )
            )
            dpg_m = float(np.exp(ln_mean))
            sigma = float(np.exp(ln_sigma))
        else:
            psd_dp = np.array(
                [dpg_m],
                dtype=float,
            )
            weights = np.array(
                [1.0],
                dtype=float,
            )
            psd_source = "Diámetro representativo único"

        Dc = convert(
            self.Dc.get(),
            self.Dc_unit.get(),
            LENGTH,
        )

        n = int(
            float(
                self.n_cyclones.get()
            )
        )

        Ne = float(
            self.Ne.get()
        )

        K = float(
            self.K_loss.get()
        )

        design_pressure_value = float(
            self.design_pressure.get()
        )
        design_pressure_gauge_pa = convert(
            design_pressure_value,
            self.design_pressure_unit.get(),
            PRESSURE,
        )

        if self.pressure_mode.get() == "Vacío":
            design_pressure_gauge_pa = -abs(
                design_pressure_gauge_pa
            )
        else:
            design_pressure_gauge_pa = abs(
                design_pressure_gauge_pa
            )

        return {
            "Q": Q,
            "T": T_K,
            "P": P,
            "rho_air": rho_air,
            "mu_air": mu_air,
            "rho_particle": rho_particle,
            "dpg_m": dpg_m,
            "sigma": sigma,
            "psd_dp": psd_dp,
            "weights": weights,
            "psd_source": psd_source,
            "Dc": Dc,
            "n": n,
            "Ne": Ne,
            "K": K,
            "material": self.material.get(),
            "cyclone_type": self.cyclone_type.get(),
            "construction_material": self.construction_material.get(),
            "pressure_mode": self.pressure_mode.get(),
            "design_pressure_gauge_pa": design_pressure_gauge_pa,
        }

    def calculate_gui(self):
        try:
            d = self.read_inputs()

            # MODELO DE PROCESO:
            # calculate() combina geometría del ciclón, propiedades del gas,
            # granulometría, eficiencia y pérdida de presión. La base teórica
            # principal es EPA [R1-R2] y Perry [R3]. Son correlaciones de
            # prediseño y deben validarse cuando el desempeño sea crítico.
            r = calculate(
                d["Q"],
                d["T"],
                d["P"],
                d["rho_air"],
                d["mu_air"],
                d["rho_particle"],
                d["Dc"],
                d["n"],
                d["cyclone_type"],
                d["psd_dp"],
                d["weights"],
                d["Ne"],
                d["K"],
            )

            self.data = d
            self.result = r
            self.psd_dp = d["psd_dp"]
            self.psd_weights = d["weights"]
            self.comparison = []

            try:
                self.structural_result = structural_screening(
                    r,
                    d,
                    **self._get_structural_settings(),
                )
            except Exception:
                self.structural_result = None

            self.show_page("results")

        except Exception as exc:
            messagebox.showerror(
                "Error de cálculo",
                str(exc),
            )

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    def export_csv(self):
        try:
            if not self.result:
                messagebox.showinfo(
                    "Sin resultados",
                    "Primero realice un cálculo.",
                )
                return

            rows = (
                self.comparison
                if self.comparison
                else [self.result]
            )

            filename = filedialog.asksaveasfilename(
                title="Guardar resultados",
                defaultextension=".csv",
                filetypes=[
                    ("CSV", "*.csv"),
                    ("Todos", "*.*"),
                ],
            )

            if not filename:
                return

            with open(
                filename,
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)

                writer.writerow([
                    "Dc_m",
                    "V_entrada_m_s",
                    "Can_velocity_m_s",
                    "Reynolds",
                    "dpc_um",
                    "Eficiencia_global_pct",
                    "DeltaP_Pa",
                    "Ciclones",
                ])

                for r in rows:
                    writer.writerow([
                        r.Dc,
                        r.V_in,
                        r.V_can,
                        r.Reynolds,
                        r.dpc * 1e6,
                        r.eta_global * 100,
                        r.deltaP,
                        r.n_cyclones,
                    ])

            messagebox.showinfo(
                "Guardado",
                f"Resultados guardados en:\n{filename}",
            )

        except Exception as exc:
            messagebox.showerror(
                "Error",
                str(exc),
            )

    # --------------------------------------------------------
    # PDF DE DISEÑO / CAD
    # --------------------------------------------------------

    def export_pdf(self):
        """Genera un PDF técnico con las dimensiones necesarias para
        modelar preliminarmente el ciclón en CAD."""
        try:
            if not self.result:
                messagebox.showinfo(
                    "Sin resultados",
                    "Primero realice un cálculo.",
                )
                return

            if not REPORTLAB_AVAILABLE:
                messagebox.showerror(
                    "Falta ReportLab",
                    "Instale ReportLab con:\\n\\npip install reportlab",
                )
                return

            filename = filedialog.asksaveasfilename(
                title="Exportar memoria PDF para diseño CAD",
                defaultextension=".pdf",
                filetypes=[
                    ("PDF", "*.pdf"),
                    ("Todos", "*.*"),
                ],
            )

            if not filename:
                return

            self.generate_pdf(filename)

            messagebox.showinfo(
                "PDF generado",
                (
                    "Se generó la memoria técnica en PDF.\\n\\n"
                    "Incluye las dimensiones, parámetros de proceso, "
                    "geometría, valores derivados y recomendaciones para "
                    "el modelado CAD preliminar."
                ),
            )

        except Exception as exc:
            messagebox.showerror(
                "Error al generar PDF",
                str(exc),
            )

    def generate_pdf(self, filename):
        r = self.result
        d = self.data
        g = r.geometry

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="SYCSA_Title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(NAVY),
            alignment=TA_CENTER,
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="SYCSA_H2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor(NAVY),
            spaceBefore=8,
            spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="SYCSA_Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor(TEXT),
        ))
        styles.add(ParagraphStyle(
            name="SYCSA_Note",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor(MUTED),
        ))

        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title="SYCSAtech - Memoria de cálculo de ciclón",
            author="SYCSAtech",
        )

        story = []

        story.append(
            Paragraph(
                "SYCSAtech",
                styles["SYCSA_Title"],
            )
        )
        story.append(
            Paragraph(
                "MEMORIA DE CÁLCULO Y DATOS PARA MODELADO CAD",
                styles["SYCSA_Title"],
            )
        )
        story.append(
            Paragraph(
                f"Calculador de Ciclones V18 — {g.name}",
                styles["SYCSA_Body"],
            )
        )
        story.append(Spacer(1, 5 * mm))

        # Input table
        story.append(
            Paragraph(
                "1. Datos de proceso y material",
                styles["SYCSA_H2"],
            )
        )

        input_data = [
            ["Parámetro", "Valor", "Unidad"],
            ["Material", d["material"], "-"],
            ["Caudal total", f"{d['Q']:.8f}", "m³/s"],
            ["Caudal por ciclón", f"{r.Q_cyclone:.8f}", "m³/s"],
            ["Temperatura", f"{d['T']:.2f}", "K"],
            ["Presión absoluta", f"{d['P']:.2f}", "Pa"],
            ["Densidad del aire", f"{d['rho_air']:.7f}", "kg/m³"],
            ["Viscosidad del aire", f"{d['mu_air']:.6e}", "Pa·s"],
            ["Densidad de partícula", f"{d['rho_particle']:.3f}", "kg/m³"],
            ["dpg", f"{d['dpg_m']*1e6:.3f}", "µm"],
            ["σg", f"{d['sigma']:.4f}", "-"],
            ["PSD", d.get("psd_source", "No especificada"), "-"],
            ["Ciclones en paralelo", str(r.n_cyclones), "-"],
            ["Material de construcción", d["construction_material"], "-"],
            ["Condición mecánica", d["pressure_mode"], "-"],
            ["Presión/vacío de diseño",
             f"{d['design_pressure_gauge_pa']/1000:.3f}", "kPa(g)"],
        ]

        t = Table(
            input_data,
            colWidths=[75 * mm, 70 * mm, 25 * mm],
            repeatRows=1,
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor(BORDER)),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)

        # CAD dimensions
        story.append(
            Paragraph(
                "2. Tabla de dimensiones para modelado CAD",
                styles["SYCSA_H2"],
            )
        )

        cone_height = max(g.H - g.h, 0)
        cone_half_angle = math.degrees(
            math.atan2((g.Dc - g.B) / 2, cone_height)
        ) if cone_height > 0 else 0
        cone_included_angle = 2 * cone_half_angle

        mech = mechanical_design_recommendation(
            d["construction_material"],
            d["pressure_mode"],
            d["design_pressure_gauge_pa"],
            r.Dc,
        )

        cad_rows = [
            ["Parámetro", "Símbolo", "Valor", "Unidad", "Uso en CAD"],
            ["Diámetro del ciclón", "Dc", f"{r.Dc:.6f}", "m", "Diámetro cuerpo"],
            ["Ancho de entrada", "a", f"{g.a:.6f}", "m", "Ancho entrada tangencial"],
            ["Altura de entrada", "b", f"{g.b:.6f}", "m", "Altura entrada tangencial"],
            ["Diámetro salida gas", "De", f"{g.De:.6f}", "m", "Tubo vortex finder"],
            ["Inmersión salida", "S", f"{g.S:.6f}", "m", "Longitud interna salida"],
            ["Altura cilíndrica", "h", f"{g.h:.6f}", "m", "Cuerpo cilíndrico"],
            ["Altura total", "H", f"{g.H:.6f}", "m", "Envolvente total"],
            ["Diámetro inferior", "B", f"{g.B:.6f}", "m", "Inicio/salida del cono"],
            ["Altura del cono", "H-h", f"{cone_height:.6f}", "m", "Tramo cónico"],
            ["Ángulo semicono", "α", f"{cone_half_angle:.3f}", "°", "Inclinación respecto eje"],
            ["Ángulo incluido", "2α", f"{cone_included_angle:.3f}", "°", "Ángulo total del cono"],
            ["Área de entrada", "Ae", f"{r.area_inlet:.8f}", "m²", "Comprobación de flujo"],
            ["Velocidad entrada", "Vi", f"{r.V_in:.5f}", "m/s", "Condición de diseño"],
            ["Diámetro circular equivalente", "Deq", f"{inlet_pipe_recommendation(r)['deq_m']:.6f}", "m", "Entrada circular"],
            ["Tipo entrada recomendado", "-", "Tubería calibrada / Schedule 10/10S", "-", "Con transición circular-tangencial"],
            ["Área cilíndrica", "Ac", f"{math.pi*r.Dc**2/4:.8f}", "m²", "Sección cuerpo"],
            ["Can velocity", "Vcan", f"{r.V_can:.5f}", "m/s", "Indicador de diseño"],
            ["Espesor estructural nominal", "t", f"{structural['selected_nominal_mm']:.1f}", "mm", "Screening preliminar"],
            ["Anillos rigidizadores", "N", str(structural["rings"]), "-", "Prediseño de rigidización"],
        ]

        t2 = Table(
            cad_rows,
            colWidths=[50*mm, 18*mm, 30*mm, 18*mm, 60*mm],
            repeatRows=1,
        )
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.2),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (1,1), (3,-1), "CENTER"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(t2)

        story.append(
            Paragraph(
                "Nota CAD: esta tabla contiene las dimensiones geométricas "
                "calculadas por el modelo. El programa no determina espesores "
                "de pared, bridas, soldaduras, tolerancias, refuerzos, soportes, "
                "material de construcción ni detalles de fabricación. Estos "
                "elementos deben definirse en ingeniería mecánica.",
                styles["SYCSA_Note"],
            )
        )

        inlet_rec = inlet_pipe_recommendation(r)

        story.append(
            Paragraph(
                "3. Detalle de entrada circular para CAD",
                styles["SYCSA_H2"],
            )
        )

        inlet_rows = [
            ["Parámetro", "Valor", "Unidad"],
            ["Área rectangular equivalente Ae", f"{inlet_rec['area_rect_m2']:.8f}", "m²"],
            ["Diámetro circular equivalente Deq", f"{inlet_rec['deq_m']*1000:.2f}", "mm"],
            ["Velocidad con área equivalente", f"{inlet_rec['velocity_m_s']:.3f}", "m/s"],
            ["Construcción sugerida", "Tubería calibrada o Schedule 10/10S", "-"],
            ["Transición", "Circular → tangencial", "-"],
        ]

        ti = Table(
            inlet_rows,
            colWidths=[75*mm, 65*mm, 25*mm],
            repeatRows=1,
        )
        ti.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(TEAL_DARK)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(ti)

        story.append(
            Paragraph(
                "<b>Recomendación:</b> conservar aproximadamente el área de la "
                "entrada rectangular calculada y seleccionar una tubería circular "
                "cuyo diámetro interior real sea igual o ligeramente mayor que "
                f"Deq = {inlet_rec['deq_m']*1000:.1f} mm. Usar una transición "
                "circular-tangencial; no conectar un tubo circular directamente "
                "como un orificio sin transición. Para dimensiones comerciales "
                "consultar ASME B36.10/B36.10M para acero al carbón y "
                "ASME B36.19/B36.19M para acero inoxidable.",
                styles["SYCSA_Note"],
            )
        )

        # Biblioteca y selección de tubería comercial
        pipe_rec = pipe_candidates(
            r,
            d["construction_material"],
            float(self.vmin.get()),
            float(self.vmax.get()),
        )

        story.append(
            Paragraph(
                "4. Selección preliminar de tubería para entrada circular",
                styles["SYCSA_H2"],
            )
        )

        if pipe_rec["available"]:
            sel = pipe_rec["selected"]
            pipe_rows = [
                ["Parámetro", "Resultado", "Unidad"],
                ["Norma dimensional", pipe_rec["standard"], "-"],
                ["Diámetro equivalente Deq", f"{pipe_rec['deq_m']*1000:.2f}", "mm"],
                ["NPS recomendado", sel["nps"], "-"],
                ["DN", str(sel["dn"]), "-"],
                ["Schedule", sel["schedule"], "-"],
                ["Diámetro exterior OD", f"{sel['od_mm']:.2f}", "mm"],
                ["Espesor nominal", f"{sel['wall_mm']:.2f}", "mm"],
                ["Diámetro interior ID", f"{sel['id_mm']:.2f}", "mm"],
                ["Velocidad en tubería", f"{sel['velocity_m_s']:.3f}", "m/s"],
                ["Criterio", pipe_rec["selection_basis"], "-"],
            ]

            tpipes = Table(
                pipe_rows,
                colWidths=[70*mm, 70*mm, 25*mm],
                repeatRows=1,
            )
            tpipes.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor(TEAL_DARK)),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 7.5),
                ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),
                 [colors.white, colors.HexColor("#F5F8FC")]),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
            ]))
            story.append(tpipes)

            story.append(
                Paragraph(
                    "<b>Nota:</b> se separan dos criterios: diámetro equivalente que conserva "
                    "aproximadamente el área de entrada y diámetro comercial que "
                    "alcanza Vmin–Vmax. Si la velocidad geométrica no cumple, "
                    "aumentar el diámetro de tubería no la corrige; debe revisarse "
                    "Dc, el número de ciclones o la geometría de entrada. "
                    "El Schedule/espesor requiere verificación mecánica.",
                    styles["SYCSA_Note"],
                )
            )
        else:
            story.append(
                Paragraph(
                    pipe_rec["message"],
                    styles["SYCSA_Note"],
                )
            )

        story.append(PageBreak())

        # Performance
        story.append(
            Paragraph(
                "5. Resultados de desempeño",
                styles["SYCSA_H2"],
            )
        )

        perf = [
            ["Resultado", "Valor", "Unidad"],
            ["Diámetro de corte", f"{r.dpc*1e6:.4f}", "µm"],
            ["Eficiencia global", f"{r.eta_global*100:.3f}", "%"],
            ["Pérdida de presión", f"{r.deltaP:.2f}", "Pa"],
            ["Pérdida de presión", f"{r.deltaP/1000:.3f}", "kPa"],
            ["Reynolds", f"{r.Reynolds:.5e}", "-"],
            ["Tiempo de residencia aprox.", f"{r.residence_time:.6f}", "s"],
            ["Ne", f"{self.data['Ne']:.3f}", "-"],
            ["Factor K", f"{self.data['K']:.3f}", "-"],
        ]

        tp = Table(
            perf,
            colWidths=[90*mm, 55*mm, 25*mm],
            repeatRows=1,
        )
        tp.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(TEAL_DARK)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
        ]))
        story.append(tp)

        # PSD
        story.append(
            Paragraph(
                "6. Distribución granulométrica utilizada",
                styles["SYCSA_H2"],
            )
        )

        psd_rows = [["Diámetro (µm)", "Fracción masa", "% masa"]]
        for dp, wt in zip(d["psd_dp"], d["weights"]):
            psd_rows.append([
                f"{dp*1e6:.4f}",
                f"{wt:.6f}",
                f"{wt*100:.3f}",
            ])

        # Limit table to a reasonable PDF size; the actual calculation
        # still uses the complete PSD.
        if len(psd_rows) > 61:
            psd_rows = psd_rows[:61]
            psd_rows.append([
                "...",
                "...",
                "PSD completa utilizada en cálculo",
            ])

        tpsd = Table(
            psd_rows,
            colWidths=[65*mm, 50*mm, 40*mm],
            repeatRows=1,
        )
        tpsd.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
        ]))
        story.append(tpsd)

        # Structural screening
        structural = structural_screening(
            r,
            d,
            **self._get_structural_settings(),
        )

        story.append(
            Paragraph(
                "7. Prediseño estructural — screening",
                styles["SYCSA_H2"],
            )
        )

        structural_rows = [
            ["Concepto", "Valor", "Unidad"],
            ["Presión externa de diseño", f"{structural['P_external_kPa']:.3f}", "kPa"],
            ["Presión interna de diseño", f"{structural['P_internal_kPa']:.3f}", "kPa"],
            ["Corrosion allowance", f"{structural['corrosion_mm']:.2f}", "mm"],
            ["Eficiencia de soldadura", f"{structural['weld_eff']:.3f}", "-"],
            ["Factor de seguridad", f"{structural['FS']:.2f}", "-"],
            ["Espesor nominal seleccionado", f"{structural['selected_nominal_mm']:.1f}", "mm"],
            ["Espesor neto", f"{structural['selected_net_mm']:.1f}", "mm"],
            ["Anillos rigidizadores", str(structural["rings"]), "-"],
            ["P admisible cilindro", f"{structural['p_allow_cyl_kPa']:.3f}", "kPa"],
            ["P admisible cono", f"{structural['p_allow_cone_kPa']:.3f}", "kPa"],
            ["P admisible gobernante", f"{structural['p_allow_structural_kPa']:.3f}", "kPa"],
            ["Utilización", f"{structural['utilization']*100:.2f}", "%"],
            ["Estado", structural["status"], "-"],
            ["Tapa", structural["head_recommendation"], "-"],
            ["Tapa plana, espesor preliminar", f"{structural['flat_head_nominal_mm']:.1f}", "mm"],
        ]

        ts = Table(
            structural_rows,
            colWidths=[75*mm, 65*mm, 25*mm],
            repeatRows=1,
        )
        ts.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(ts)
        story.append(
            Paragraph(
                "<b>Advertencia:</b> el screening de pandeo no sustituye "
                "la verificación de presión externa del código aplicable. "
                "La utilización y el espesor seleccionado son herramientas "
                "de prediseño para CAD.",
                styles["SYCSA_Note"],
            )
        )

        # Mechanical / CAD material recommendation
        story.append(
            Paragraph(
                "8. Recomendación preliminar de construcción CAD",
                styles["SYCSA_H2"],
            )
        )

        mech = mechanical_design_recommendation(
            d["construction_material"],
            d["pressure_mode"],
            d["design_pressure_gauge_pa"],
            r.Dc,
        )

        mech_rows = [
            ["Concepto", "Recomendación"],
            ["Material seleccionado", mech["material"]],
            ["Condición", mech["severity"]],
            ["Presión/vacío de diseño",
             f"{mech['pressure_kpa']:.3f} kPa"],
            ["Espesor preliminar de lámina",
             f"{mech['recommended_sheet_mm']:.1f} mm"],
            ["Tapa / cabezal",
             mech["head_recommendation"]],
            ["Rigidización",
             mech["stiffener_recommendation"]],
            ["Comentario de material",
             mech["material_note"]],
        ]

        tm = Table(
            mech_rows,
            colWidths=[55*mm, 105*mm],
            repeatRows=1,
        )
        tm.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
        ]))
        story.append(tm)

        story.append(Spacer(1, 3*mm))
        story.append(
            Paragraph(
                "<b>ADVERTENCIA DE DISEÑO MECÁNICO:</b> El espesor anterior es "
                "una recomendación preliminar de especificación para iniciar "
                "el CAD; no es un espesor calculado por ASME. En vacío, el "
                "modo crítico puede ser pandeo por presión externa y depende "
                "fuertemente de Dc, longitud libre, ovalidad, tolerancias, "
                "rigidizadores, soldaduras y condiciones de fabricación. "
                "El diseño definitivo debe verificarse con el código aplicable.",
                styles["SYCSA_Note"],
            )
        )

        # Base teórica detallada
        story.append(
            Paragraph(
                "10. Base teórica de las ecuaciones",
                styles["SYCSA_H2"],
            )
        )

        theory_paragraphs = [
            "<b>Geometría Stairmand.</b> Las dimensiones se expresan como fracciones de Dc para conservar similitud geométrica. Base: Stairmand (1951) [R1].",
            "<b>Continuidad.</b> Qc=Q/N, Ae=a·b y Vi=Qc/Ae provienen del balance de caudal. La velocidad de entrada afecta eficiencia y presión [R3, R6].",
            "<b>Reynolds.</b> Re=rho·Vi·Dc/mu relaciona fuerzas inerciales y viscosas [R5, R7].",
            "<b>Diámetro de corte.</b> dpc=sqrt(9·mu·b/[2·pi·Ne·Vi·(rho_p-rho_g)]) corresponde al modelo clásico de Lapple presentado en EPA/APTI [R2, R5].",
            "<b>Eficiencia fraccional.</b> eta=1/[1+(dpc/dp)²] es una correlación de prediseño con eta=0.5 en dp=dpc [R2, R5].",
            "<b>Eficiencia global.</b> eta_global=sum(eta_i·w_i) pondera la eficiencia por la PSD [R5].",
            "<b>Pérdida de presión.</b> DeltaP=K·rho·Vi²/2 representa la pérdida como múltiplo de presión dinámica. K debe validarse para la geometría real [R3, R4, R6].",
            "<b>Entrada circular.</b> Deq=sqrt(4·Ae/pi) conserva el área de la entrada rectangular como primera aproximación para CAD.",
            "<b>Screening estructural.</b> Se emplean equilibrio de membrana y pandeo elástico simplificado. No sustituyen ASME VIII-1 [R8, R9].",
        ]
        for ptxt in theory_paragraphs:
            story.append(Paragraph(ptxt, styles["SYCSA_Note"]))
            story.append(Spacer(1, 1.5*mm))

        # Referencias bibliográficas y base teórica
        story.append(
            Paragraph(
                "11. Referencias bibliográficas (formato APA)",
                styles["SYCSA_H2"],
            )
        )

        references_text = [
            "<b>[R1]</b> Stairmand, C. J. (1951). The design and performance of cyclone separators. <i>Transactions of the Institution of Chemical Engineers, 29</i>, 356–383.",
            "<b>[R2]</b> Lapple, C. E. (1951). Processes use many collector types. <i>Chemical Engineering, 58</i>, 144–151.",
            "<b>[R3]</b> Shepherd, C. B., &amp; Lapple, C. E. (1939). Flow pattern and pressure drop in cyclone dust collectors. <i>Industrial &amp; Engineering Chemistry, 31</i>(8), 972–984. https://doi.org/10.1021/ie50356a012",
            "<b>[R4]</b> Leith, D., &amp; Mehta, D. (1973). Cyclone performance and design. <i>Atmospheric Environment, 7</i>(5), 527–549. https://doi.org/10.1016/0004-6981(73)90006-1",
            "<b>[R5]</b> U.S. Environmental Protection Agency. (1981). <i>APTI Course 413: Control of particulate emissions</i>. Air Pollution Training Institute.",
            "<b>[R6]</b> U.S. Environmental Protection Agency. (2003). <i>Air pollution control technology fact sheet: Cyclones</i> (EPA-452/F-03-005).",
            "<b>[R7]</b> Hoffmann, A. C., &amp; Stein, L. E. (2002). <i>Gas cyclones and swirl tubes: Principles, design, and operation</i>. Springer. https://doi.org/10.1007/978-3-662-07377-3",
            "<b>[R8]</b> ASME. <i>Boiler and Pressure Vessel Code, Section VIII, Division 1</i>. American Society of Mechanical Engineers.",
            "<b>[R9]</b> ASME. <i>Boiler and Pressure Vessel Code, Section II, Part D</i>. American Society of Mechanical Engineers.",
            "<b>[R10]</b> ASME. <i>B36.10/B36.10M: Welded and seamless wrought steel pipe</i>. American Society of Mechanical Engineers.",
            "<b>[R11]</b> ASME. <i>B36.19/B36.19M: Stainless steel pipe</i>. American Society of Mechanical Engineers.",
        ]

        for ref in references_text:
            story.append(Paragraph(ref, styles["SYCSA_Note"]))
            story.append(Spacer(1, 1.5*mm))

        story.append(
            Paragraph(
                "<b>Nota:</b> Las relaciones de eficiencia y pérdida de presión "
                "son correlaciones de prediseño. El módulo estructural es un "
                "screening simplificado y no reproduce íntegramente ASME "
                "UG-28/UG-29 ni constituye una certificación.",
                styles["SYCSA_Note"],
            )
        )

        # Recommendations
        story.append(
            Paragraph(
                "12. Recomendaciones de diseño",
                styles["SYCSA_H2"],
            )
        )

        recs = recommendations(
            r,
            d["material"],
            d["dpg_m"] * 1e6,
            d["sigma"],
            float(self.vmin.get()),
            float(self.vmax.get()),
            float(self.eta_target.get()),
            float(self.dp_max.get()),
        )

        rec_rows = [["Tipo", "Recomendación"]]
        for kind, title, msg in recs:
            rec_rows.append([
                title,
                msg,
            ])

        tr = Table(
            rec_rows,
            colWidths=[55*mm, 105*mm],
            repeatRows=1,
        )
        tr.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#F5F8FC")]),
        ]))
        story.append(tr)

        story.append(Spacer(1, 5 * mm))

        story.append(
            Paragraph(
                "13. Alcance y advertencia de ingeniería",
                styles["SYCSA_H2"],
            )
        )

        story.append(
            Paragraph(
                "Este documento es una memoria de prediseño. Las dimensiones "
                "geométricas se generan mediante las relaciones de la geometría "
                f"{g.name}. Antes de fabricar el equipo deben verificarse la "
                "granulometría real, concentración de sólidos, caudal real, "
                "presión, temperatura, desgaste, material de construcción, "
                "espesores, uniones, soportes, cargas, conexión a ductos, "
                "descarga de sólidos, filtración posterior y requisitos "
                "normativos aplicables. El PDF está pensado para proporcionar "
                "los valores base necesarios para iniciar el modelo 3D CAD, "
                "no como plano de fabricación certificado.",
                styles["SYCSA_Body"],
            )
        )

        story.append(Spacer(1, 5 * mm))

        story.append(
            Paragraph(
                "SYCSAtech © 2026 — Ingeniería que mueve tus ideas",
                styles["SYCSA_Note"],
            )
        )

        def footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor(BORDER))
            canvas.line(
                15*mm,
                10*mm,
                A4[0] - 15*mm,
                10*mm,
            )
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.drawString(
                15*mm,
                6*mm,
                "SYCSAtech - Calculador de Ciclones",
            )
            canvas.drawRightString(
                A4[0] - 15*mm,
                6*mm,
                f"Página {doc.page}",
            )
            canvas.restoreState()

        doc.build(
            story,
            onFirstPage=footer,
            onLaterPages=footer,
        )

    def export_report(self):
        try:
            if not self.result:
                messagebox.showinfo(
                    "Sin resultados",
                    "Primero realice un cálculo.",
                )
                return

            filename = filedialog.asksaveasfilename(
                title="Guardar informe",
                defaultextension=".txt",
                filetypes=[
                    ("Informe TXT", "*.txt"),
                    ("Todos", "*.*"),
                ],
            )

            if not filename:
                return

            Path(filename).write_text(
                self.generate_report_text(),
                encoding="utf-8",
            )

            messagebox.showinfo(
                "Informe",
                f"Informe guardado en:\n{filename}",
            )

        except Exception as exc:
            messagebox.showerror(
                "Error",
                str(exc),
            )

    # --------------------------------------------------------
    # PLOTS
    # --------------------------------------------------------

    def preview_psd(self):
        try:
            d = self.read_inputs()

            plt.figure(figsize=(9, 6))
            plt.semilogx(
                d["psd_dp"] * 1e6,
                d["weights"] / max(d["weights"]) * 100,
                marker="o" if d["psd_source"] == "PSD medida introducida por tabla" else None,
                linewidth=2,
            )
            plt.axvline(
                d["dpg_m"] * 1e6,
                linestyle="--",
                label=f"dpg={d['dpg_m']*1e6:.1f} µm",
            )
            plt.xlabel("Diámetro de partícula (µm)")
            plt.ylabel("PSD normalizada (%)")
            plt.title(
                f"PSD - {d['material']}"
            )
            plt.grid(
                True,
                which="both",
                alpha=0.3,
            )
            plt.legend()
            plt.tight_layout()
            plt.show()

        except Exception as exc:
            messagebox.showerror(
                "PSD",
                str(exc),
            )

    # --------------------------------------------------------
    # ABOUT
    # --------------------------------------------------------

    def about(self):
        messagebox.showinfo(
            "Acerca de",
            (
                "SYCSAtech - Calculador de Ciclones V5.0\n\n"
                "Herramienta de prediseño para separación sólido-gas.\n\n"
                "Módulos: proceso, resultados, geometría, partículas, "
                "comparación, recomendaciones e informe.\n\n"
                "Los resultados deben validarse antes de utilizarse "
                "como diseño definitivo."
            ),
        )


# ============================================================
# MAIN
# ============================================================

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
