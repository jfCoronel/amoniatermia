# Referencia de mercado para el capítulo 13: fuentes de datos

29/09/2026. Resultado de una búsqueda sobre qué publica EPREL y dónde están el
refrigerante y la carga (decisión de H5, opción C, en `DECISIONES_2026_09_29.md`). Los
ejemplos son de fuente primaria salvo que se indique. Hay que volver a comprobarlos al
construir la muestra.

## EPREL

- **Grupo de producto**: `spaceheaters` (Reg. (UE) 811/2013). Los paquetes están en
  `spaceheaterpackages` y las bombas de calor de solo ACS en `waterheaters` (812/2013).
- **Acceso**:
  - Hay búsqueda web pública (https://eprel.ec.europa.eu/screen/product/spaceheaters).
  - La ficha individual por número de registro no pide clave (`/api/products/spaceheaters/<n>`).
  - Los **listados sí la piden**: sin ella devuelven 403. Se solicita en el sitio («Request
    Public API Key»), y las condiciones de uso admiten la investigación.
  - No hay exportación masiva pública.
- **Publica** η_s a 35 y 55 °C en los tres climas, P_rated por clima y temperatura, clase,
  consumo anual, potencia acústica y, en los combinados, η_wh con su perfil de carga.
- **No publica** el SCOP (se deduce: η_s = SCOP/2.5·100 − 3 %), **ni refrigerante, ni
  carga, ni GWP, ni datos de refrigeración**.

## Dónde están el refrigerante, la carga y el modo frío

- **Heat Pump Keymark** (hoja de datos del anexo D1): refrigerante, masa de refrigerante,
  y P_designc y SEER en modo frío cuando procede.
  - https://keymark.eu/en/products/heatpumps
  - Base nueva: certificates.keymark.eu, aplicación web; no se ha comprobado si permite
    exportar.
- **hplib (FZJ)**: extracción de Keymark con refrigerante, carga y SCOP. Datos de 04/2023,
  sin R-744. https://github.com/FZJ-IEK3-VSA/hplib
- **Lista BAFA** (08/2023): P_rated, η_s35, η_s55 y refrigerante; sin modo frío.
- **Fichas técnicas de los fabricantes.**

## Ejemplos encontrados (clima medio)

| Equipo | Refrig. | η_s35 / η_s55 | SCOP 35 / 55 | Carga | Frío |
|---|---|---|---|---|---|
| Panasonic Aquarea J, WH-MDC09J3E5 (9 kW) | R-32 | 193 / 130 % | 4.90 / 3.32 | 1.3 kg | 9.0 kW, EER 2.71 (A35W7) |
| Daikin Altherma 3 M, EBLA09DW1 (9 kW) | R-32 | 190 / 135 % | 4.82 / 3.44 | 3.80 kg | SEER 5.62; EER 3.35 (A35W7) |
| Panasonic T-CAP M, WH-WXG09ME5 (9 kW) | R-290 | 195 / 140 % | 4.96 / 3.57 | 1.78 kg | EER 3.61 (A35W7) |
| Vaillant aroTHERM plus VWL 105/8.1 (11 kW) | R-290 | — / 151 % | — | — | — |

**R-744**: no se han encontrado equipos aire-agua de calefacción de 6 a 12 kW con datos
ErP. Lo que hay son **bombas de calor de ACS**: Sanden SANCO2 (4.5 kW, unos 0.62 kg) y
Panasonic CO₂ de 4 y 6 kW. La referencia de mercado del R-744 tendría que hacerse en
**modo ACS** (812/2013, η_wh), frente a M-5 y no frente a la calefacción.

## Decisión del autor (29/09/2026)

La muestra se construye con **Heat Pump Keymark**. El R-744 se nombra y **queda fuera**:
solo existe como bomba de calor de ACS, la máquina no está diseñada para producir ACS
(M-5 es secundario, con consigna reducida a 45 °C) y la comparación saldría sesgada. La
referencia de mercado queda con R-32 y R-290.

## Consecuencias para el plan

1. Hace falta una **clave de la API de EPREL**, que se pide en el sitio (la gestiona el
   autor), o bien construir la muestra a mano desde la búsqueda web. **Keymark** es la
   fuente que da a la vez indicadores, refrigerante, carga y modo frío.
2. El criterio de la muestra (monobloc aire-agua reversible de 6 a 12 kW en clima medio a
   35 °C) sirve para R-32 y R-290. Para R-744 la muestra tiene que ser de **bombas de calor
   de ACS**.
3. EPREL da η_s a 35 y 55 °C, que confirma la necesidad de calcular el SCOP de la máquina
   en esas dos aplicaciones además de a 45 °C.

## Fuentes

- https://eprel.ec.europa.eu/api/product-groups
- https://ec.europa.eu/assets/move-ener/eprel/EPREL%20Public/Public%20API%20Term%20and%20Conditions/API_TERMS_AND_CONDITIONS_EN.pdf
- https://www.heatpumpkeymark.com/fileadmin/user_upload/documents/HPK0020_Annex-D1_Data-sheet-template_V21-1.pdf
- https://keymark.eu/en/documents/heat-pumps/118-heat-pump-keymark-scheme-rules-v15/file
- https://www.energie-experten.org/fileadmin/Newsartikel/Newsartikel_07/BAFA-Liste_foerderfaehige_Waermepumpen_08-2023.pdf
- https://www.aircon.panasonic.eu/IE_en/model/wh-mdc09j3e5-1/
- https://www.acae.es/catalogos/daikin/fiebdc/e-b-d-la09-16d-3-v3-w1-eeden20-data-books-english.pdf
- https://www.panasonicproclub.com/uploads/MK/catalogues/EU%2020P%20PRINT%20AQUAREA%20M%2024%20LR.pdf
- https://www.vaillant.de/api/download/product/de/erp-datenblatt_arotherm-plus_782705.pdf
- https://static1.squarespace.com/static/5c1a79ca96d455dcbffdc742/t/5c474cee562fa759dd733b04/1548176625850/Sanden_sanc02_technical-info_10-2017_4.pdf
- https://www.pv-magazine.com/2026/06/29/panasonic-launches-co%E2%82%82-air-to-water-heat-pump-with-coefficient-of-performance-of-6-1/
