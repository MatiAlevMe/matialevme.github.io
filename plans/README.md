# MatiAlevMe Portfolio — Plan Maestro

> Portfolio profesional con temática **Persona 4 Golden** (vibra RPG/UI de videojuego).
> Inspirado en el estilo de menú de Persona 5 ([Omicron69/persona5-style-portfolio](https://github.com/Omicron69/persona5-style-portfolio))
> adaptado a la paleta amarilla, más juvenil y "magazine pop" de Persona 4 Golden.

---

## Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Paleta de Colores](#paleta-de-colores)
3. [Tipografía](#tipografía)
4. [Estructura de Pantallas](#estructura-de-pantallas)
5. [Navegación](#navegación)
6. [Stack Tecnológico](#stack-tecnológico)
7. [Assets Visuales](#assets-visuales)
8. [Estructura de Archivos](#estructura-de-archivos)
9. [Sync de Datos (guia-laboral)](#sync-de-datos-guia-laboral)
10. [Privacidad](#privacidad)
11. [Roadmap](#roadmap)

---

## Visión General

Single-page portfolio que simula la interfaz de un videojuego RPG.
El usuario navega entre "pantallas" (Home, Projects, Skills, About, Contact)
con transiciones suaves, sonido opcional y controles de teclado.

### Screens

| # | Pantalla | Contenido |
|---|----------|-----------|
| 1 | **HOME** | Nombre grande, subtítulo, menú principal con 4 botones |
| 2 | **PROJECTS** | Grid de proyectos con cards expandibles + repos de GitHub |
| 3 | **SKILLS** | Barras de habilidad categorizadas con nivel (LV.) |
| 4 | **ABOUT** | Bio, foto polaroid, CV download, education + certs |
| 5 | **CONTACT** | Formulario de email + enlaces a redes |

---

## Paleta de Colores

Basada en la UI de Persona 4 Golden:

```css
--p4-yellow:       #FFB300;   /* Primary - amarillo dorado */
--p4-yellow-light: #FFD740;   /* Hover / highlight */
--p4-yellow-dark:  #E6A200;   /* Active / border */
--p4-dark:         #1a1a2e;   /* Secondary - gris oscuro profundo */
--p4-darker:       #0b0b0d;   /* Background principal */
--p4-blue:         #4FC3F7;   /* Accent - celeste */
--p4-white:        #f6f4ef;   /* Texto claro */
--p4-red:          #C22303;   /* Acento secundario (uso moderado) */
--p4-green:        #66BB6A;   /* Online / success */
```

---

## Tipografía

| Uso | Fuente | Peso |
|-----|--------|------|
| Títulos grandes (HOME name) | `Outfit`, sans-serif | 800 / 900 |
| Headers de pantalla | `Outfit`, sans-serif | 700 |
| Texto body | `Inter`, sans-serif | 300 / 400 / 500 |
| Etiquetas HUD / teclas | `Inter`, sans-serif | 600 (uppercase) |
| Mono (código) | `JetBrains Mono` | 400 |

**No usar fuentes personalizadas del juego** (copyright Atlus).
Las fuentes elegidas dan la misma "vibra" sin problemas legales.

---

## Estructura de Pantallas

La página tiene 5 pantallas. Solo UNA se muestra a la vez.
El estado se maneja con JS vanilla.

```
┌─────────────────────────────────┐
│  HUD TOP (name + tagline)       │
├─────────────────────────────────┤
│                                 │
│  ┌───────────────────────────┐  │
│  │   SCREEN ACTIVE           │  │
│  │   (display: block)        │  │
│  │                           │  │
│  └───────────────────────────┘  │
│                                 │
├─────────────────────────────────┤
│  HUD BOTTOM (↑↓ Select, Enter) │
└─────────────────────────────────┘
```

Cada pantalla tiene:
- `data-screen="home|projects|skills|about|contact"` en el body
- Clase `screen` + `.active` para la visible
- Transición wipe al cambiar

---

## Navegación

### Teclado (igual que Persona 5 reference)

| Tecla | Acción |
|-------|--------|
| `↑` `↓` | Navegar items del menú |
| `Enter` | Confirmar / entrar a pantalla |
| `Esc` | Volver a HOME |
| Click en nombre | Volver a HOME |

### Click

- Los botones del menú HOME navegan a su pantalla
- Botón "Back" o ESC en sub-pantallas vuelve a HOME

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Framework | Astro 5 (SSG) |
| CSS Base | Tailwind CSS 3 |
| CSS Tema | Custom `p4-theme.css` (variables + estilos P4) |
| Interactividad | Vanilla JS (controller pattern tipo MVC) |
| Formulario | FormSubmit.co (POST a email) |
| Build | `npm run build` → `dist/` |
| Deploy | GitHub Actions → GitHub Pages |
| Sync datos | `scripts/extract.py` + GH Action semanal |

---

## Assets Visuales

### Generados por código (CSS/SVG)
- Rayas diagonales amarillas (fondo) — `repeating-linear-gradient`
- TV static overlay — CSS noise texture
- Estrellas / formas geométricas — SVG inline
- Placeholder de proyectos — SVG con nombre + gradiente
- Tarjetas, botones, HUD — CSS puro

### Imágenes externas (tú debes agregarlas)

Para mantener la vibra Persona 4, busca imágenes **libres de derecho** o **fan art con permiso**:

| Archivo | Ubicación | Descripción | Tamaño recomendado |
|---------|-----------|-------------|-------------------|
| `hero-art.png` | `public/images/` | Arte principal del héroe (personaje ilustración) al lado del menú HOME. Transparente PNG ideal. | 900x1200px |
| `bg-home.jpg` | `public/images/` | Fondo para pantalla HOME (paisaje Inaba, TV world, etc.) | 1920x1080px |
| `bg-projects.jpg` | `public/images/` | Fondo para pantalla PROJECTS | 1920x1080px |
| `bg-skills.jpg` | `public/images/` | Fondo para pantalla SKILLS | 1920x1080px |
| `bg-about.jpg` | `public/images/` | Fondo para pantalla ABOUT | 1920x1080px |
| `bg-contact.jpg` | `public/images/` | Fondo para pantalla CONTACT | 1920x1080px |
| `me.jpg` | `public/images/` | Tu foto para la sección About (estilo polaroid) | 400x500px |
| `fireguard.png` | `public/images/` | Screenshot del proyecto FireGuard | 1200x675px (16:9) |
| `kineviz.png` | `public/images/` | Screenshot del proyecto KineViz | 1200x675px |
| `mcp-server.png` | `public/images/` | Screenshot/logo del proyecto MCP Server | 1200x675px |

**Qué buscar específicamente:**
- **Fondos de pantalla P4G en 1920x1080** — paisajes de Inaba (río, escuela, centro comercial), TV world, niebla amarilla
- **Fan art del Investigation Team** — solo con permiso del artista o etiquetado para reuso
- **Arte vectorial minimalista amarillo/negro** — no necesita ser de Persona, solo la vibra: geometría amarilla sobre negro, texturas de TV static
- **Texturas de ruido / static** — imágenes PNG con ruido para superponer como overlay

---

## Sync de Datos (guia-laboral)

El CV está en `E:\repos\guia-laboral\cv\` como archivos `.adoc`.
El script `scripts/extract.py`:
1. Busca `guia-laboral/` como sibling directory (local) o lo clona via GH Action
2. Parsea `cv-es.adoc` y `cv-en.adoc`
3. Hace merge inteligente con `portfolio.json` existente (preserva imágenes, videos, personalizaciones)
4. Genera `src/data/portfolio.json` actualizado

**Importante:** `guia-laboral` es privado. En GitHub Actions se necesita un `GH_PAT` (Personal Access Token)
con scope `repo` para clonarlo. Configurado como secret del repo.

---

## Privacidad

- **Información sensible de clientes/empresas NO debe estar en este repo público**
- Para mostrar material confidencial a empresas, usar un repo privado separado
- El portfolio público contiene solo lo que está en `portfolio.json` (curado manualmente)
- Las imágenes de proyectos deben ser screenshots públicos o placeholders

---

## Roadmap

### Fase 1: Fundación (completado)
- [x] Proyecto Astro inicializado
- [x] `portfolio.json` con datos curados
- [x] `extract.py` funcional
- [x] Deploy a GitHub Pages
- [x] `.nojekyll` para evitar Jekyll

### Fase 2: Bugfixes + Infra
- [ ] Fix extract.py: education, experience, volunteer, project parsing
- [ ] GH_PAT en workflow para sync de guia-laboral
- [ ] Placeholder images para proyectos sin screenshot

### Fase 3: Rediseño Persona 4
- [ ] Tema CSS P4 (colores, rayas, TV static, HUD)
- [ ] Componentes P4 (Shell, Home, Projects, Skills, About, Contact)
- [ ] Navegación screen-based con teclado + click
- [ ] Transiciones wipe entre pantallas
- [ ] Skill bars con rank
- [ ] Project cards estilo P4

### Fase 4: Features
- [ ] Formulario de contacto (FormSubmit.co)
- [ ] Animaciones scroll/hover
- [ ] Responsive design
- [ ] Assets visuales (imágenes de fondo, hero art)
- [ ] Sonidos de menú (opcional)

---

## Referencias

- [Persona 5 Style Portfolio](https://github.com/Omicron69/persona5-style-portfolio) — inspiración de código y diseño
- [Persona 4 Golden - Game UI Database](https://www.gameuidatabase.com/gameData.php?id=595) — screenshots de UI de referencia
- [Persona 4 Golden Color Palette](https://www.color-hex.com/color-palette/9358) — paleta de colores
- [FormSubmit.co](https://formsubmit.co/) — servicio de formularios sin backend
