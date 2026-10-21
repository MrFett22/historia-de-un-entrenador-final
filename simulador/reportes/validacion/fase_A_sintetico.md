# Fase A en datos sintéticos (verdad conocida)

Celdas técnico × club × temporada (≥ 8 partidos): 113 · técnicos: 30 · clubes: 18 · temporadas: 6

Regla pre-registrada: f_θ = σ_θ² / (σ_θ² + σ_φ² + σ_int²); si su percentil 2.5 < 0.05 → plantel.

| componente | f_θ mediana | f_θ IC 95 % | σ_θ | σ_φ | σ_int (p97.5) | σ_Δ | R̂ máx | ESS mín | método | decisión |
|---|---|---|---|---|---|---|---|---|---|---|
| int_at[Directa] | 0.42 | [0.116, 0.77] | 0.114 | 0.126 | 0.030 (0.099) | 0.052 | 1.0069 | 649 | NUTS | tecnico |
| int_at[Ataque elaborado] | 0.27 | [0.003, 0.64] | 0.106 | 0.153 | 0.068 (0.162) | 0.059 | 1.0026 | 880 | NUTS | plantel |
| int_co[Directa] | 0.26 | [0.002, 0.64] | 0.098 | 0.080 | 0.139 (0.202) | 0.040 | 1.0049 | 781 | NUTS | plantel |
| int_co[Ataque elaborado] | 0.56 | [0.079, 0.88] | 0.137 | 0.087 | 0.080 (0.156) | 0.025 | 1.0087 | 486 | NUTS | tecnico |
| s_marcador | 0.35 | [0.001, 0.97] | 0.250 | 0.241 | 0.161 (0.438) | 0.129 | 1.0091 | 627 | NUTS | plantel |
| s_rival | 0.21 | [0.001, 0.93] | 0.110 | 0.091 | 0.163 (0.448) | 0.134 | 1.0059 | 870 | NUTS | plantel |
| l_at | 0.16 | [0.024, 0.42] | 0.093 | 0.206 | 0.038 (0.104) | 0.049 | 1.0054 | 537 | NUTS | plantel |
| l_co | 0.60 | [0.251, 0.84] | 0.135 | 0.091 | 0.054 (0.116) | 0.030 | 1.0032 | 1215 | NUTS | tecnico |
| u_at[Directa] | 0.38 | [0.025, 0.84] | 0.130 | 0.139 | 0.077 (0.179) | 0.028 | 1.0064 | 451 | NUTS | plantel |
| u_at[Circulación estéril] | 0.10 | [0.000, 0.84] | 0.037 | 0.093 | 0.036 (0.112) | 0.045 | 1.0058 | 736 | NUTS | plantel |
| u_at[Ataque elaborado] | 0.20 | [0.009, 0.56] | 0.099 | 0.184 | 0.044 (0.124) | 0.054 | 1.0052 | 1280 | NUTS | plantel |
| u_co[Directa] | 0.10 | [0.001, 0.54] | 0.075 | 0.205 | 0.062 (0.166) | 0.078 | 1.0034 | 1064 | NUTS | plantel |
| u_co[Circulación estéril] | 0.18 | [0.001, 0.88] | 0.084 | 0.058 | 0.151 (0.248) | 0.067 | 1.0055 | 673 | NUTS | plantel |
| u_co[Ataque elaborado] | 0.31 | [0.007, 0.79] | 0.087 | 0.117 | 0.042 (0.123) | 0.048 | 1.0065 | 773 | NUTS | plantel |
| w_at[Directa] | 0.16 | [0.000, 0.81] | 0.042 | 0.069 | 0.053 (0.104) | 0.025 | 1.0085 | 472 | NUTS | plantel |
| w_at[Circulación estéril] | 0.46 | [0.005, 0.96] | 0.065 | 0.048 | 0.038 (0.102) | 0.045 | 1.0070 | 787 | NUTS | plantel |
| w_at[Ataque elaborado] | 0.11 | [0.002, 0.38] | 0.057 | 0.155 | 0.028 (0.086) | 0.027 | 1.0059 | 904 | NUTS | plantel |
| w_co[Directa] | 0.31 | [0.013, 0.63] | 0.114 | 0.123 | 0.112 (0.185) | 0.044 | 1.0061 | 955 | NUTS | plantel |
| w_co[Circulación estéril] | 0.51 | [0.004, 0.98] | 0.073 | 0.040 | 0.047 (0.113) | 0.026 | 1.0087 | 824 | NUTS | plantel |
| w_co[Ataque elaborado] | 0.45 | [0.015, 0.80] | 0.129 | 0.086 | 0.106 (0.187) | 0.026 | 1.0053 | 977 | NUTS | plantel |
| rho[corner] | 0.12 | [0.001, 0.44] | 0.070 | 0.170 | 0.066 (0.139) | 0.039 | 1.0087 | 539 | NUTS | plantel |
| rho[tiro_libre_area] | 0.04 | [0.000, 0.38] | 0.039 | 0.175 | 0.031 (0.096) | 0.066 | 1.0049 | 1054 | NUTS | plantel |
| rho[lateral_largo] | 0.14 | [0.000, 0.82] | 0.068 | 0.139 | 0.071 (0.170) | 0.063 | 1.0057 | 999 | NUTS | plantel |
| rho[tiro_libre_directo] | 0.48 | [0.007, 0.97] | 0.117 | 0.075 | 0.070 (0.194) | 0.095 | 1.0058 | 934 | NUTS | plantel |
| nu_at[corner] | 0.11 | [0.000, 0.65] | 0.093 | 0.231 | 0.098 (0.247) | 0.084 | 1.0083 | 806 | NUTS | plantel |
| nu_at[tiro_libre_area] | 0.25 | [0.001, 0.94] | 0.072 | 0.078 | 0.070 (0.199) | 0.040 | 1.0068 | 1087 | NUTS | plantel |
| nu_at[lateral_largo] | 0.09 | [0.000, 0.59] | 0.120 | 0.275 | 0.238 (0.509) | 0.247 | 1.0073 | 822 | NUTS | plantel |
| nu_co[corner] | 0.18 | [0.001, 0.75] | 0.095 | 0.166 | 0.080 (0.214) | 0.039 | 1.0085 | 740 | NUTS | plantel |
| nu_co[tiro_libre_area] | 0.48 | [0.003, 0.97] | 0.128 | 0.069 | 0.089 (0.226) | 0.041 | 1.0025 | 1358 | NUTS | plantel |
| nu_co[lateral_largo] | 0.28 | [0.001, 0.95] | 0.140 | 0.137 | 0.126 (0.357) | 0.227 | 1.0057 | 896 | NUTS | plantel |
| alpha | 0.90 | [0.604, 1.00] | 0.280 | 0.065 | 0.049 (0.151) | 0.061 | 1.0064 | 710 | NUTS | tecnico |
| gamma | 0.83 | [0.367, 0.98] | 0.346 | 0.130 | 0.066 (0.211) | 0.070 | 1.0087 | 472 | NUTS | tecnico |

Componentes del técnico: 5 de 32; del plantel: 27; en la liga: 0.

Cobertura global de θ (T-A1): 0.912; σ verdaderas dentro del 95 %: 87/96 (T-A2); w_at (σ_θ = 0 en la verdad) → plantel (T-A3); todas las componentes con R̂ < 1.01 y ESS > 400 (T-A4).