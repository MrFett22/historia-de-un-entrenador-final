# El modelo

Notación: $i$ es el equipo que ataca y $j$ el que defiende; $t = 0,\dots,89$ es el minuto;
$\tau(t)$ es el tramo de 15 minutos; $m \in \{\text{pierde}, \text{empata}, \text{gana}\}$ es el
estado del marcador visto desde $i$. El desarrollo completo está en
`estudio/docs/04_MODELO_MATEMATICO.md` (vocabulario) y en `simulador/reportes/MODELO.md`
(simulador).

## 1. Vocabulario: cadena absorbente y mezcla de tres tipos de jugada

Cortamos cada posesión en secuencias, desde su inicio hasta su primera absorción. Una
secuencia es un recorrido del balón por una malla de $5\times4$ zonas (20 estados
transitorios) que termina en uno de cinco estados absorbentes: gol, remate, pérdida, balón
fuera o interrupción. Si escribimos la matriz de transición en bloques,
$P=\begin{pmatrix} Q & R\\ 0 & I\end{pmatrix}$, entonces

$$N=(I-Q)^{-1},\qquad t=N\mathbf 1,\qquad B=NR,$$

donde $t$ da las acciones esperadas hasta la absorción y $B$ la probabilidad de cada final.

Las secuencias de la liga no salen de una sola cadena. Las modelamos como una mezcla de
$K=3$ cadenas, cada una con su propia matriz para el primer paso, $P^{0,k}$:

$$\Pr(s)=\sum_{k=1}^{3}\pi_k\,\mu^k_{z_1}\,P^{0,k}_{z_1z_2}\prod_{t\ge2}P^{k}_{z_tz_{t+1}}.$$

Estimamos la mezcla en el estudio con EM-MAP (prior de Dirichlet hacia la cadena de la liga).
El simulador usa ese mismo vocabulario, tal cual, en vez de reajustarlo. Los tres tipos son el
ataque directo (unas 3.5 acciones; 14 % termina en remate), el toque sin profundidad (unas 6.7
acciones; 2 a 3 %) y el ataque elaborado (unas 9.2 acciones; 12 %). Cada secuencia $s$ recibe
su probabilidad $r_{sk}$ de pertenecer a cada tipo.

## 2. El partido: M1 a M4 y la intensidad de gol

Cada equipo tiene una ficha $\zeta_i$ de 32 componentes, medidas como desviaciones de la liga.

M1, número de jugadas por minuto:
$$\lambda_i(t)=\bar\lambda_{\tau(t)}\exp\!\big(l^{at}_i+l^{co}_j+h\,(2\,\text{local}_i-1)\big).$$

M2, tipo de jugada según el contexto (logit multinomial con el toque sin profundidad como
referencia):
$$\eta_{ik}=b_{0k}+\text{int}^{at}_{i,k}+\text{int}^{co}_{j,k}+(1+s^{\,marc}_i)\big(b^{pierde}_k[m=\text{pierde}]+b^{gana}_k[m=\text{gana}]\big)+b^{tf}_k[\tau=6]+b^{loc}_k\,\text{local}_i+(1+s^{\,riv}_i)\,b^{elo}_k\tfrac{\Delta\text{Elo}}{100},$$
$$\pi_{ik}(t,m)=\operatorname{softmax}_k(\eta_{ik}).$$

M3, eficiencia de cada tipo: la probabilidad de remate
$p_{ik}=\operatorname{expit}\!\big(\operatorname{logit}\bar p_k+u^{at}_{i,k}+u^{co}_{j,k}\big)$ y el xG por
remate $g_{ik}=\bar g_k\,e^{\,w^{at}_{i,k}+w^{co}_{j,k}}$.

M4, balón parado por tipo de saque $u$: la frecuencia $\bar r_u e^{\rho_{i,u}}$, la probabilidad
de rematar $q_{iju}=\operatorname{expit}(\operatorname{logit}\bar q_u+\nu^{at}_{i,u}+\nu^{co}_{j,u})$ y el
xG del remate $\kappa_u$, que tomamos de la liga.

Con $f$ igual al cociente goles/xG de la liga, la intensidad de gol por minuto y estado del
marcador es
$$\mu_{ij}(t,m)=f\Big[\lambda_i(t)\sum_k\pi_{ik}(t,m)\,p_{ik}\,g_{ik}+\sum_u \bar r_u e^{\rho_{i,u}}\,q_{iju}\,\kappa_u\Big].$$

## 3. Recursión exacta del marcador

Sea $P_t(a,b)$ la probabilidad de ir $a$–$b$ al empezar el minuto $t$. En cada minuto, $i$ anota
$X\sim\text{Poisson}(\mu_{ij}(t,m))$ y $j$ anota $Y\sim\text{Poisson}(\mu_{ji}(t,2-m))$:

$$P_{t+1}(a+x,b+y)=\sum_{a,b}P_t(a,b)\,\text{Pois}\big(x;\mu_{ij}(t,m_{ab})\big)\,\text{Pois}\big(y;\mu_{ji}(t,2-m_{ab})\big).$$

Como $\mu$ solo depende del signo de $a-b$, el paso se separa por regiones del marcador:
$P_{t+1}=\sum_m T_A[m]\,(P_t\circ\mathbf 1_m)\,T_B[m]^\top$, con matrices de Toeplitz. Así
obtenemos la distribución exacta del marcador final (hasta 15 goles por lado, con masa perdida
menor a $10^{-6}$). De ella salen $P(\text{gana})$, $P(\text{empata})$, los puntos esperados
(xPts) y los goles esperados por tipo de jugada.

## 4. Técnico, plantel e interacción

Estimamos en dos etapas. En la primera, cada componente se estima por celda técnico × club ×
torneo (con al menos 8 partidos), con su varianza agrupada por partido. En la segunda, un
modelo bayesiano de efectos cruzados separa al técnico del plantel:

$$y_c\sim\mathcal N\big(b_0+\varphi_{\text{club},\text{torneo}}+\theta_{\text{técnico}}+\varepsilon_{\text{técnico},\text{club}},\ v_c\big),$$
$$\varphi_{\text{club},t}\sim\mathcal N(\varphi_{\text{club},t-1},\sigma_\Delta),\quad \theta\sim\mathcal N(0,\sigma_\theta),\quad \varepsilon\sim\mathcal N(0,\sigma_{int}).$$

Lo ajustamos con NUTS (PyMC y numpyro). La parte del técnico en cada componente es
$f_\theta=\sigma_\theta^2/(\sigma_\theta^2+\sigma_\varphi^2+\sigma_{int}^2)$.

Usamos atribución continua. La ficha del América con el técnico $T^*$ es
$\zeta=b_0+\varphi_{Am}+\theta_{T^*}+\varepsilon_{T^*,Am}$ en todas las componentes, con la
posterior completa de $\theta$, encogida por $\sigma_\theta$. De este modo el técnico pesa lo
que los datos permiten distinguir. La regla original de todo o nada (el técnico solo cuenta si
el percentil 2.5 de $f_\theta$ supera 0.05) resultaba inalcanzable bajo el prior; la
conservamos solo como etiqueta descriptiva.

## 5. El torneo

Jugamos los 153 partidos del calendario real del Apertura 2026 con Monte Carlo en dos niveles:
$R$ muestras de la posterior de las fichas (incertidumbre de los parámetros) y, en cada una,
$S$ torneos (azar de los partidos). Los marcadores se sortean de la distribución exacta. Para
comparar dos técnicos usamos los mismos números aleatorios, de modo que la diferencia no
mezcla azar ajeno. Los puntos esperados de cada réplica son exactos ($\sum$ xPts) y el error de
Monte Carlo es

$$\operatorname{Var}(\bar X)=\frac{\sigma_b^2}{R}+\frac{\sigma_w^2}{RS}.$$

El veredicto de una comparación usa un margen de equivalencia de ±3 puntos por torneo. Es
"prácticamente igual" si el intervalo del 90 % de la diferencia cabe en $(-3,3)$; es "mejor" o
"peor" si el del 95 % excluye el 0.
