# Modelo del simulador (ecuaciones implementadas)

`modelo_simulador.tex` no estaba disponible (D-002); estas son las ecuaciones que implementa el
código, escritas desde 04_ESPECIFICACION.md. Notación: i ataca, j defiende; t = minuto 0..89;
τ(t) = tramo de 15 minutos (6 tramos); m = estado del marcador de i (pierde, empata, gana);
ζ_i = ficha del equipo i (32 componentes, desviaciones de la liga, `tipos.COMPONENTES`).

## Vocabulario: mezcla de K = 3 cadenas con paso inicial (`estimacion/mezcla.py`, D-047)
Pr(s ∣ k) = μ^k[z₁] · P0^k[z₁, z₂] · ∏_{t≥2} P^k[z_t, z_{t+1}]  (la PRIMERA acción de la secuencia tiene su propia matriz P0; ADR-v2-29 de dtcoach).
E[T ∣ k] = μ^k (1 + Q^{0,k} t^k), P(absorción ∣ k) = μ^k (R^{0,k} + Q^{0,k} B^k), con t = N 1, B = N R de la cadena P^k.
EM-MAP con prior Dirichlet fijo hacia la liga (λ para P, λ0 para P0, a0 para μ); los tipos se encuentran con el modelo atado (P0 = P, escalera
ADR-v2-17) y después se libera P0. Fuente: `estudio/src/dtcoach/mezcla.py`. Las responsabilidades r_sk (de las que salen p̄, ḡ y b_liga)
usan la verosimilitud con P0.

**Vocabulario fijo de la fuente (`calibrar --vocab-dtcoach`, D-048).** Con esa opción no se ajusta el EM: (π, μ, P, P0) son los de `mezcla_K3.npz` de dtcoach y
r_sk = P(k ∣ s) se toma de `responsabilidades_K3.parquet` donde la secuencia se empareja con una de simdt, y de la verosimilitud con la mezcla de la fuente en el resto.

**Multiarranque (D-049).** El EM se corre desde varias semillas y se conserva la solución de mayor J, que se calcula con el mismo prior y los mismos datos para todos los arranques.

## Atribución al técnico (fase A, D-051)
ζ_América(T*) = b0 + φ_Am + θ_T* + ε_T*,Am para TODAS las componentes, con la posterior completa de θ (encogida por σ_θ). f_θ = σ_θ² / (σ_θ² + σ_φ² + σ_int²) y la regla
"p2.5 < 0.05 → efecto del técnico poco distinguible" son una etiqueta descriptiva; ya no apagan componentes (los artefactos anteriores, sin `meta.atribucion`, se leen con la regla binaria).
Perillas: θ de cada perilla se recorta al 90 % central de θ ~ N(0, σ_θ) con σ_θ de su posterior. Δ entre dos técnicos incluye la incertidumbre de θ de ambos.

## M1 — llegadas de juego abierto (`modelos/llegada.py`)
λ_i(t) = λ̄[τ(t)] · exp(l_at,i + l_co,j + h·(2·local_i − 1))

## M2 — tipos de jugada (`modelos/familias.py`)
η_ik(t,m) = b0_k + int_at,i[k] + int_co,j[k] + (1 + s_marcador,i)·(b_pierde,k·[m=pierde] + b_gana,k·[m=gana])
          + b_tf,k·[τ = 6] + b_loc,k·local_i + (1 + s_rival,i)·b_elo,k·ΔElo/100,   η_i,ref = 0
π_ik(t,m) = softmax_k(η_ik)

## M3 — eficiencia (`modelos/eficiencia.py`)
p_ik = expit(logit p̄_k + u_at,i[k] + u_co,j[k]),   g_ik = ḡ_k · exp(w_at,i[k] + w_co,j[k])

## M4 — balón parado (`modelos/balon_parado.py`)
saques_iu(t) = r̄_u[τ] · exp(rho_i[u] + h_bp·(2·local_i − 1))      (penal: solo liga, D-010)
q_iju = expit(logit q̄_u + nu_at,i[u] + nu_co,j[u])   (capa 1; = 1 en tiro libre directo y penal)
goles por saque = q_iju · κ_u   (capa 2, portero y definición = liga; H9)

## Intensidad (`modelos/intensidad.py`)
μ_ij(t,m) = λ_i(t) Σ_k π_ik(t,m) p_ik g_ik + Σ_u saques_iu(t) q_iju κ_u

## Recursión exacta del marcador (`motor/partido.py`)
P_{t+1}(a+x, b+y) = Σ P_t(a,b) · Pois(x; μ_ij(t, m(a,b))) · Pois(y; μ_ji(t, 2 − m(a,b)))
Como μ solo depende del signo de a − b, el paso es separable por región:
P_{t+1} = Σ_m T_A[m] (P_t ∘ 1[m]) T_B[m]ᵀ con matrices Toeplitz de la Poisson. G = 15 (D-018),
sin truncamiento por minuto (D-017). Masa perdida < 1e-6 (T-P2).
Salidas: P_T, P(gana/empata/pierde), xPts, E[goles] (= Σ_t Σ_m ocupación·μ, T-P4), ocupación de m,
E[N_k] = Σ_t Σ_m ocup·λπ_k, E[goles_k], E[goles_bp,u].

## M5 — zonas (`modelos/cadena.py`)
v^k = μ^k + μ^k Q^{0,k} N^k con las cadenas de la LIGA (H3; Q^{0,k} = bloque transitorio de P0^k, el primer paso); mapa = Σ_k E[N_k] v^k.
Artefactos anteriores a D-047 no traen P0: se usa P en el primer paso (v^k = μ^k N^k).

## Cambios (`modelos/cambios.py`, descriptivo, H11)
hazard(t,m) = expit(base[t] + c_m + alpha_i), t = 45..89;  P(tipo|m) ∝ exp(base[m,tipo] + gamma_i·(tipo − 1))

## Fase A — ficha de un equipo (`estimacion/`)
ζ_c = φ[club, temporada] + θ[técnico] + ε[técnico, club]  (m = 0 por construcción);
temporada = torneo corto (Apertura o Clausura, 17 jornadas).

## Temporada (`motor/temporada.py`) y error de Monte Carlo de dos etapas
Para un número X que se promedia sobre R réplicas externas (muestras de parámetros) y S torneos
internos por réplica: Var(X̄) = σ_b²/R + σ_w²/(R·S), con σ_b² = varianza entre réplicas de la media
condicional y σ_w² = varianza media dentro de la réplica. Con costo C = R·(c_R + S·c_S), el S que
minimiza la varianza a costo fijo es S* = sqrt(c_R·σ_w² / (c_S·σ_b²)).
Los puntos esperados por réplica se calculan exactos (Σ xPts), así que su σ_w = 0.
