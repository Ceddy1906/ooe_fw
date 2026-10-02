// Erzeugt icon.svg und die PNG-Icons (kein externes Paket nötig): node tools/make-icon.js
const fs = require("fs");
const zlib = require("zlib");
const path = require("path");

// Flammen-Umrisse als Bézier-Segmente (Koordinaten 0..256)
const OUTER = "M128 24 C140 70 196 96 196 154 C196 196 166 228 128 228 C90 228 60 196 60 154 C60 124 78 106 92 92 C94 112 104 124 114 124 C104 90 112 52 128 24 Z";
const INNER = "M128 130 C138 150 160 166 160 188 C160 208 146 222 128 222 C110 222 96 208 96 188 C96 166 118 152 128 130 Z";

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E53935"/><stop offset="1" stop-color="#B71C1C"/></linearGradient></defs>
  <rect width="256" height="256" rx="56" fill="url(#bg)"/>
  <path d="${OUTER}" fill="#FFFFFF"/>
  <path d="${INNER}" fill="#FF9800"/>
</svg>
`;

function flatten(d) {
  const t = d.match(/[MCZ]|-?\d+(\.\d+)?/g);
  const pts = [];
  let i = 0, cur = [0, 0];
  while (i < t.length) {
    const c = t[i++];
    if (c === "M") { cur = [+t[i++], +t[i++]]; pts.push(cur); }
    else if (c === "C") {
      const p1 = [+t[i++], +t[i++]], p2 = [+t[i++], +t[i++]], p3 = [+t[i++], +t[i++]];
      for (let s = 1; s <= 24; s++) {
        const u = s / 24, v = 1 - u;
        pts.push([
          v*v*v*cur[0] + 3*v*v*u*p1[0] + 3*v*u*u*p2[0] + u*u*u*p3[0],
          v*v*v*cur[1] + 3*v*v*u*p1[1] + 3*v*u*u*p2[1] + u*u*u*p3[1],
        ]);
      }
      cur = p3;
    }
  }
  return pts;
}
const inPoly = (x, y, p) => {
  let r = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    if ((p[i][1] > y) !== (p[j][1] > y) &&
        x < ((p[j][0] - p[i][0]) * (y - p[i][1])) / (p[j][1] - p[i][1]) + p[i][0]) r = !r;
  }
  return r;
};
const inRound = (x, y, r = 56) => {
  const cx = Math.min(Math.max(x, r), 256 - r), cy = Math.min(Math.max(y, r), 256 - r);
  return (x - cx) ** 2 + (y - cy) ** 2 <= r * r;
};

const outer = flatten(OUTER), inner = flatten(INNER);
const lerp = (a, b, t) => Math.round(a + (b - a) * t);

function render(size) {
  const SS = 4, raw = Buffer.alloc((size * 4 + 1) * size);
  for (let py = 0; py < size; py++) {
    raw[py * (size * 4 + 1)] = 0;
    for (let px = 0; px < size; px++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let sy = 0; sy < SS; sy++) for (let sx = 0; sx < SS; sx++) {
        const x = ((px + (sx + .5) / SS) / size) * 256, y = ((py + (sy + .5) / SS) / size) * 256;
        if (!inRound(x, y)) continue;
        let c;
        if (inPoly(x, y, inner)) c = [255, 152, 0];
        else if (inPoly(x, y, outer)) c = [255, 255, 255];
        else c = [lerp(0xE5, 0xB7, y / 256), lerp(0x39, 0x1C, y / 256), lerp(0x35, 0x1C, y / 256)];
        r += c[0]; g += c[1]; b += c[2]; a++;
      }
      const o = py * (size * 4 + 1) + 1 + px * 4, n = SS * SS;
      if (a) { raw[o] = r / a; raw[o + 1] = g / a; raw[o + 2] = b / a; }
      raw[o + 3] = Math.round((a / n) * 255);
    }
  }
  return raw;
}

const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0;
});
const crc = (buf) => { let c = 0xFFFFFFFF; for (const b of buf) c = crcTable[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
const chunk = (type, data) => {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const c = Buffer.alloc(4); c.writeUInt32BE(crc(td));
  return Buffer.concat([len, td, c]);
};
function png(size) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(render(size), { level: 9 })), chunk("IEND", Buffer.alloc(0)),
  ]);
}

const root = path.join(__dirname, "..");
const brand = path.join(root, "custom_components", "ooelfv_einsaetze", "brand");
fs.writeFileSync(path.join(root, "icon.svg"), svg);
fs.writeFileSync(path.join(brand, "icon.png"), png(256));
fs.writeFileSync(path.join(brand, "icon@2x.png"), png(512));
console.log("Icons erzeugt");
