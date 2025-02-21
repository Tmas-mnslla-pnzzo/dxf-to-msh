import ezdxf
import csv
import numpy as np
import triangle
import matplotlib.pyplot as plt
from math import cos, sin, pi
from config import *
from geometria import leer_entidades_dxf_por_capa, generar_malla_triangle, guardar_malla_vtk, guardar_malla_npz, guardar_malla_csv,  visualizar_malla

if len(sys.argv) < 2:
    print("Error: Debes proporcionar el nombre del archivo.")
    sys.exit(1) 

ruta = sys.argv[1]
ruta_dxf = ruta + ".dxf"

puntos_contorno, segmentos_contorno, conj_puntos_agujeros, conj_segmentos_agujeros, clasificaciones_contorno, clasificaciones_agujeros = leer_entidades_dxf_por_capa(
    ruta_dxf, prefijo_capa_agujeros, num_intermedios_linea, num_intermedios_circulo, 
    num_intermedios_spline, indice_punto_contorno, indice_punto_agujero, densidad
)

malla = generar_malla_triangle(
    puntos_contorno, segmentos_contorno, conj_puntos_agujeros, 
    conj_segmentos_agujeros, max_area, clasificaciones_contorno, clasificaciones_agujeros
)

if op_vtk:
    guardar_malla_vtk(ruta, malla)
if op_npz:
    guardar_malla_npz(ruta, malla)
if op_csv:
    guardar_malla_csv(ruta, malla)
if op_vis:
    visualizar_malla(malla)
