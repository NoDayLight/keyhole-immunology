# KEYHOLE vendored browser runtime

Every file in this directory is a **byte-exact copy** of a file taken from an official,
exact-pinned upstream distribution. Nothing here is minified, transpiled, bundled,
re-generated, or edited by KEYHOLE. These files are inlined into the standalone offline
report by `keyhole.vendor`; the report performs no CDN fetch, runtime import, remote
texture load, external font request, network request, or `eval`.

Acquisition used the public npm registry over HTTPS at authoring time only. The runtime
never contacts a network.

## three@0.169.0 — MIT

- Upstream tarball: `https://registry.npmjs.org/three/-/three-0.169.0.tgz`
- Tarball npm integrity: `sha512-Ed906MA3dR4TS5riErd4QBsRGPcx+HBDX2O5yYE5GqJeFQTPU+M56Va/f/Oph9X7uZo3W3o4l2ZhBZ6f6qUv0w==`
- Retained member: `package/build/three.module.min.js` → `three/three.module.min.js`
  - 687,458 bytes, SHA-256 `f7cee3c7533449a1505cc12cb5128b89e3d4fd3d7ea62b05f9f5464a217472ee`
- Retained member: `package/LICENSE` → `three/LICENSE`
  - 1,081 bytes, SHA-256 `4c40a1ef62450b857c3b2aaf294936304cd552d965fbcd9d32d4c5bcf4ba4454`
- SPDX: `MIT` (Copyright 2010-2024 Three.js Authors; the license header is retained inside
  the distribution file itself).

`0.169.0` is the **last** three.js release whose minified ES-module build is a single
self-contained file. It declares zero static imports, zero dynamic imports, and zero
`import.meta` references, so it can be inlined verbatim into one
`<script type="module">` element with no module resolution, import map, or blob URL.
From `0.172.0` onward `three.module.min.js` statically imports `./three.core.min.js`,
which cannot be resolved inside a single offline file. The older UMD `three.min.js`
build was rejected because it is deprecated and emits a console deprecation warning.

The report exposes the namespace with a **generated** bridge: `keyhole.vendor` parses the
single trailing `export{...}` clause of the untouched distribution and emits
`globalThis.THREE=Object.freeze({...})` for an explicit allow-list of the symbols KEYHOLE
actually uses. The distribution file is never rewritten, and report assembly fails loudly
if any required export disappears.

## cobe@0.6.4 — MIT

- Upstream tarball: `https://registry.npmjs.org/cobe/-/cobe-0.6.4.tgz`
- Tarball npm integrity: `sha512-huuGFnDoXLy/tsCZYYa/H35BBRs9cxsS0XKJ3BXjRp699cQKuoEVrvKlAQMx0DKXG7+VUv4jsHVrS7yPbkLSkQ==`
- Retained member: `package/dist/index.esm.js` → `cobe/index.esm.js`
  - 6,267 bytes, SHA-256 `f4f29c3e95e77b091b4350ec848a9aaf2dfeb262df5c876dab981badb3beed0f`
- Retained member: `package/LICENSE` → `cobe/LICENSE`
  - 1,065 bytes, SHA-256 `226e31827d99b53fe36d8476824a7238056db4c8bd8ac5abe7e73f6004fba24e`
- SPDX: `MIT` (Copyright 2021 Shu Ding). Project: <https://github.com/shuding/cobe>.

`cobe/index.esm.js` contains exactly one ES-module statement at each end of the file:
a leading `import v from"phenomenon";` and a trailing `export{p as default};`.
`keyhole.vendor` performs an **anchored** replacement of only those two exact statements
so the module body can run as a classic script, and raises if either anchor is missing.
The file on disk stays byte-exact.

cobe embeds its dot-matrix world map as a `data:image/png;base64,…` texture inside the
distribution itself, so the globe needs no remote texture. The report CSP already allows
`img-src data:`.

## phenomenon@1.6.0 — MIT

- Upstream tarball: `https://registry.npmjs.org/phenomenon/-/phenomenon-1.6.0.tgz`
- Tarball npm integrity: `sha512-7h9/fjPD3qNlgggzm88cY58l9sudZ6Ey+UmZsizfhtawO6E3srZQXywaNm2lBwT72TbpHYRPy7ytIHeBUD/G0A==`
- Retained member: `package/dist/phenomenon.umd.js` → `phenomenon/phenomenon.umd.js`
  - 5,577 bytes, SHA-256 `0765263a32157f6737429d7d83117d96ce23e29ee26160ec3304f67168543736`
- Retained member: `package/LICENSE` → `phenomenon/LICENSE`
  - 1,073 bytes, SHA-256 `67a210dd59d8eb003aad302c07db2cd9a553d03f8639e4c3815066080f388bb1`
- SPDX: `MIT` (Copyright Colin van Eenige).

This is cobe's only runtime dependency. The UMD build is used because it assigns
`window.Phenomenon` directly and therefore needs no transformation at all.

## @ibm/plex-serif@2.0.0 — SIL Open Font License 1.1

- Upstream tarball: `https://registry.npmjs.org/@ibm/plex-serif/-/plex-serif-2.0.0.tgz`
- Tarball npm integrity: `sha512-xVu9JsC18tBoQF2M6fofpsWrHj5a94saxlOZbYmXoC0E3UfjgS1JlibgrnaUJjnkLlEyCpMgI2PdhkDxijw0gA==`
- Retained member: `package/fonts/split/woff2/IBMPlexSerif-Regular-Latin1.woff2`
  → `fonts/IBMPlexSerif-Regular-Latin1.woff2`
  - 22,956 bytes, SHA-256 `324a502545695a3e8dd9e9d9273ec56e3aa2a729689807756b9439e2c7a48071`
- Retained member: `package/fonts/split/woff2/IBMPlexSerif-Italic-Latin1.woff2`
  → `fonts/IBMPlexSerif-Italic-Latin1.woff2`
  - 24,512 bytes, SHA-256 `1bceb36acfb5828f10ef9462de2003b0da6c53781faff4a942d426378d9fd975`
- Retained member: `package/LICENSE.txt` → `fonts/LICENSE.txt`
  - 4,456 bytes, SHA-256 `7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da`
- SPDX: `OFL-1.1` (Copyright 2017 IBM Corp., Reserved Font Name "Plex").

Only the weight-400 upright and weight-400 italic **Latin1** subsets are packaged. Their
upstream `unicode-range` is `U+0020-007E, U+00A0-00FF, U+0131, U+0152-0153, U+02C6,
U+02DA, U+02DC, U+2013-2014, U+2018-201A, U+201C-201E, U+2020-2022, U+2026, U+2030,
U+2039-203A, U+2044, U+20AC, U+2122, U+2212, U+FB01-FB02`, which covers every character
KEYHOLE sets in the serif display role. Glyphs outside that range (for example `β` in
`β2-microglobulin`) are only ever set in the monospace or UI-sans roles, which use
already-installed system faces and add no bytes.

The fonts are embedded as `data:font/woff2;base64` sources inside the report's inline
stylesheet. The report CSP therefore allows `font-src data:` and nothing else; no
`local()` source is declared, so rendering does not depend on locally installed fonts.

## Redistribution

MIT and OFL-1.1 both permit redistribution with their license text, which is retained
verbatim beside each artifact and inlined as an attribution comment into every generated
report. Consistent with the rest of this repository, no blanket license is asserted over
third-party assets.
