"""Standalone and Chat-Embeddable WebGL 3D HTML viewer exporter for FreeCAD MCP.

Generates zero-dependency, self-contained interactive WebGL 3D viewers compliant with
strict CSP (no external script tags except allowlisted Tailwind). Features authentic
CAD Flat Lines feature edge rendering, smooth OrbitControls, theme adaptation, and
compact card layout (< 450px) specifically optimized for inline chat embeds (<agent-embed>).
"""

import os
import json
import math
import FreeCAD


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    * { box-sizing: border-box; }
  </style>
</head>
<body class="__BODY_CLASS__">
  <div class="__CONTAINER_CLASS__">
    <!-- Header -->
    <div class="flex items-center justify-between mb-2 pb-2 border-b border-[var(--border)]">
      <div class="min-w-0 pr-2">
        <div class="font-semibold text-sm leading-tight text-[var(--foreground)] truncate">__TITLE__</div>
        <div class="text-[11px] text-[var(--muted-foreground)] truncate">__DOC_INFO__</div>
      </div>
      <div class="flex items-center gap-1.5 text-[11px] font-mono shrink-0">
        <span class="bg-[var(--secondary)] text-[var(--secondary-foreground)] px-2 py-0.5 rounded-md">
          __DIMS__ mm
        </span>
        <span class="bg-[var(--primary)] text-[var(--primary-foreground)] font-semibold px-2 py-0.5 rounded-md">
          __TRIS__ tris
        </span>
      </div>
    </div>

    <!-- 3D Canvas Box -->
    <div class="__CANVAS_WRAPPER_CLASS__">
      <canvas id="webgl-canvas" class="w-full h-full block cursor-grab active:cursor-grabbing"></canvas>
      
      <!-- Overlaid HUD Controls Bar -->
      <div class="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-[var(--card)]/85 backdrop-blur-md border border-[var(--border)] rounded-full px-3 py-1 shadow-lg text-xs z-10 select-none">
        <button id="btn-reset" class="hover:text-[var(--primary)] text-[var(--foreground)] font-medium px-2 py-0.5 rounded transition">Reset</button>
        <span class="text-[var(--border)]">|</span>
        <button id="btn-edges" class="hover:text-[var(--primary)] text-[var(--foreground)] font-medium px-2 py-0.5 rounded transition">Edges</button>
        <span class="text-[var(--border)]">|</span>
        <button id="btn-rotate" class="hover:text-[var(--primary)] text-[var(--foreground)] font-medium px-2 py-0.5 rounded transition">Rotate</button>
      </div>

      <div id="webgl-fallback" class="hidden absolute inset-0 flex items-center justify-center text-sm text-red-400 bg-black/80"></div>
    </div>

    <!-- Footer hint -->
    <div class="flex justify-between items-center mt-2 text-[11px] text-[var(--muted-foreground)]">
      <span>🖱️ Drag to orbit • Scroll to zoom • Right-drag to pan</span>
      <span class="font-mono text-[10px] text-[var(--primary)]">WebGL CAD</span>
    </div>
  </div>

  <script>
    const MODEL = __JSON_DATA__;

    // --- Mat4 Utilities ---
    function mat4Create() {
      return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
    }

    function mat4Perspective(out, fovy, aspect, near, far) {
      const f = 1.0 / Math.tan(fovy / 2);
      const nf = 1 / (near - far);
      out[0] = f / aspect; out[1] = 0; out[2] = 0; out[3] = 0;
      out[4] = 0; out[5] = f; out[6] = 0; out[7] = 0;
      out[8] = 0; out[9] = 0; out[10] = (far + near) * nf; out[11] = -1;
      out[12] = 0; out[13] = 0; out[14] = (2 * far * near) * nf; out[15] = 0;
      return out;
    }

    function mat4LookAt(out, eye, center, up) {
      let x0, x1, x2, y0, y1, y2, z0, z1, z2, len;
      const eyex = eye[0], eyey = eye[1], eyez = eye[2];
      const upx = up[0], upy = up[1], upz = up[2];
      const centerx = center[0], centery = center[1], centerz = center[2];

      z0 = eyex - centerx; z1 = eyey - centery; z2 = eyez - centerz;
      len = 1 / Math.hypot(z0, z1, z2);
      z0 *= len; z1 *= len; z2 *= len;

      x0 = upy * z2 - upz * z1; x1 = upz * z0 - upx * z2; x2 = upx * z1 - upy * z0;
      len = Math.hypot(x0, x1, x2);
      if (!len) { x0 = 0; x1 = 0; x2 = 0; } else { len = 1 / len; x0 *= len; x1 *= len; x2 *= len; }

      y0 = z1 * x2 - z2 * x1; y1 = z2 * x0 - z0 * x2; y2 = z0 * x1 - z1 * x0;
      len = Math.hypot(y0, y1, y2);
      if (!len) { y0 = 0; y1 = 0; y2 = 0; } else { len = 1 / len; y0 *= len; y1 *= len; y2 *= len; }

      out[0] = x0; out[1] = y0; out[2] = z0; out[3] = 0;
      out[4] = x1; out[5] = y1; out[6] = z1; out[7] = 0;
      out[8] = x2; out[9] = y2; out[10] = z2; out[11] = 0;
      out[12] = -(x0 * eyex + x1 * eyey + x2 * eyez);
      out[13] = -(y0 * eyex + y1 * eyey + y2 * eyez);
      out[14] = -(z0 * eyex + z1 * eyey + z2 * eyez);
      out[15] = 1;
      return out;
    }

    function mat4Multiply(out, a, b) {
      const a00=a[0], a01=a[1], a02=a[2], a03=a[3];
      const a10=a[4], a11=a[5], a12=a[6], a13=a[7];
      const a20=a[8], a21=a[9], a22=a[10], a23=a[11];
      const a30=a[12], a31=a[13], a32=a[14], a33=a[15];
      let b0 = b[0], b1 = b[1], b2 = b[2], b3 = b[3];
      out[0] = b0*a00 + b1*a10 + b2*a20 + b3*a30;
      out[1] = b0*a01 + b1*a11 + b2*a21 + b3*a31;
      out[2] = b0*a02 + b1*a12 + b2*a22 + b3*a32;
      out[3] = b0*a03 + b1*a13 + b2*a23 + b3*a33;
      b0 = b[4]; b1 = b[5]; b2 = b[6]; b3 = b[7];
      out[4] = b0*a00 + b1*a10 + b2*a20 + b3*a30;
      out[5] = b0*a01 + b1*a11 + b2*a21 + b3*a31;
      out[6] = b0*a02 + b1*a12 + b2*a22 + b3*a32;
      out[7] = b0*a03 + b1*a13 + b2*a23 + b3*a33;
      b0 = b[8]; b1 = b[9]; b2 = b[10]; b3 = b[11];
      out[8] = b0*a00 + b1*a10 + b2*a20 + b3*a30;
      out[9] = b0*a01 + b1*a11 + b2*a21 + b3*a31;
      out[10] = b0*a02 + b1*a12 + b2*a22 + b3*a32;
      out[11] = b0*a03 + b1*a13 + b2*a23 + b3*a33;
      b0 = b[12]; b1 = b[13]; b2 = b[14]; b3 = b[15];
      out[12] = b0*a00 + b1*a10 + b2*a20 + b3*a30;
      out[13] = b0*a01 + b1*a11 + b2*a21 + b3*a31;
      out[14] = b0*a02 + b1*a12 + b2*a22 + b3*a32;
      out[15] = b0*a03 + b1*a13 + b2*a23 + b3*a33;
      return out;
    }

    function mat3NormalFromMat4(out, a) {
      const a00=a[0], a01=a[1], a02=a[2];
      const a10=a[4], a11=a[5], a12=a[6];
      const a20=a[8], a21=a[9], a22=a[10];
      const b01 = a22 * a11 - a12 * a21;
      const b11 = -a22 * a10 + a12 * a20;
      const b21 = a21 * a10 - a11 * a20;
      const det = a00 * b01 + a01 * b11 + a02 * b21;
      if (!det) return null;
      const idet = 1.0 / det;
      out[0] = b01 * idet;
      out[1] = (-a22 * a01 + a02 * a21) * idet;
      out[2] = (a12 * a01 - a02 * a11) * idet;
      out[3] = b11 * idet;
      out[4] = (a22 * a00 - a02 * a20) * idet;
      out[5] = (-a12 * a00 + a02 * a10) * idet;
      out[6] = b21 * idet;
      out[7] = (-a21 * a00 + a01 * a20) * idet;
      out[8] = (a11 * a00 - a01 * a10) * idet;
      return out;
    }

    // --- Shaders ---
    const vsFaceSource = `
      attribute vec3 aPos;
      attribute vec3 aNorm;
      uniform mat4 uMVP;
      uniform mat4 uMV;
      uniform mat3 uNormMat;
      varying vec3 vNorm;
      varying vec3 vPos;
      void main() {
        vec4 mvPos = uMV * vec4(aPos, 1.0);
        vPos = mvPos.xyz;
        vNorm = normalize(uNormMat * aNorm);
        gl_Position = uMVP * vec4(aPos, 1.0);
      }
    `;

    const fsFaceSource = `
      precision mediump float;
      varying vec3 vNorm;
      varying vec3 vPos;
      uniform vec3 uColor;
      uniform vec3 uLight1;
      uniform vec3 uLight2;
      uniform float uAmbient;
      void main() {
        vec3 n = normalize(vNorm);
        if (!gl_FrontFacing) n = -n;
        vec3 l1 = normalize(uLight1);
        vec3 l2 = normalize(uLight2);
        float diff1 = max(dot(n, l1), 0.0) * 0.72;
        float diff2 = max(dot(n, l2), 0.0) * 0.32;
        vec3 v = normalize(-vPos);
        vec3 h1 = normalize(l1 + v);
        float spec = pow(max(dot(n, h1), 0.0), 28.0) * 0.28;
        vec3 col = uColor * (uAmbient + diff1 + diff2) + vec3(spec);
        gl_FragColor = vec4(col, 1.0);
      }
    `;

    const vsLineSource = `
      attribute vec3 aPos;
      uniform mat4 uMVP;
      void main() {
        gl_Position = uMVP * vec4(aPos, 1.0);
      }
    `;

    const fsLineSource = `
      precision mediump float;
      uniform vec4 uLineColor;
      void main() {
        gl_FragColor = uLineColor;
      }
    `;

    function createShader(gl, type, source) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error(gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    }

    function createProgram(gl, vs, fs) {
      const prog = gl.createProgram();
      gl.attachShader(prog, vs);
      gl.attachShader(prog, fs);
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        console.error(gl.getProgramInfoLog(prog));
        return null;
      }
      return prog;
    }

    // --- State & Setup ---
    let gl, faceProg, lineProg;
    let posBuffer, normBuffer, indexBuffer, indexType, indexCount;
    let edgeBuffer = null, edgeCount = 0;
    let showEdges = true, autoRotate = false;

    const maxDim = Math.max(MODEL.dimensions.x, MODEL.dimensions.y, MODEL.dimensions.z) || 50;
    let target = [0, 0, 0];
    let defaultRadius = maxDim * 2.2;
    let radius = defaultRadius;
    let theta = Math.PI / 4;
    let phi = Math.PI / 3;

    function initWebGL() {
      const canvas = document.getElementById('webgl-canvas');
      gl = canvas.getContext('webgl', { antialias: true, alpha: true }) || canvas.getContext('experimental-webgl');
      if (!gl) {
        document.getElementById('webgl-fallback').classList.remove('hidden');
        document.getElementById('webgl-fallback').textContent = 'WebGL is not supported in this browser.';
        return;
      }

      gl.enable(gl.DEPTH_TEST);
      gl.depthFunc(gl.LEQUAL);

      const vsFace = createShader(gl, gl.VERTEX_SHADER, vsFaceSource);
      const fsFace = createShader(gl, gl.FRAGMENT_SHADER, fsFaceSource);
      faceProg = createProgram(gl, vsFace, fsFace);

      const vsLine = createShader(gl, gl.VERTEX_SHADER, vsLineSource);
      const fsLine = createShader(gl, gl.FRAGMENT_SHADER, fsLineSource);
      lineProg = createProgram(gl, vsLine, fsLine);

      // Face buffers
      posBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(MODEL.vertices), gl.STATIC_DRAW);

      normBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, normBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(MODEL.normals), gl.STATIC_DRAW);

      const extUint = gl.getExtension('OES_element_index_uint');
      const useUint = extUint && (MODEL.vertices.length / 3 > 65535);
      indexBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      if (useUint) {
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(MODEL.indices), gl.STATIC_DRAW);
        indexType = gl.UNSIGNED_INT;
      } else {
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(MODEL.indices), gl.STATIC_DRAW);
        indexType = gl.UNSIGNED_SHORT;
      }
      indexCount = MODEL.indices.length;

      // CAD Edges buffer
      if (MODEL.edges && MODEL.edges.length > 0) {
        edgeBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, edgeBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(MODEL.edges), gl.STATIC_DRAW);
        edgeCount = MODEL.edges.length / 3;
      }

      setupInteraction(canvas);
      resizeCanvas();
      window.addEventListener('resize', resizeCanvas);
      requestAnimationFrame(render);
    }

    function resizeCanvas() {
      const canvas = document.getElementById('webgl-canvas');
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      gl.viewport(0, 0, canvas.width, canvas.height);
    }

    function render() {
      if (autoRotate) {
        theta += 0.008;
      }

      gl.clearColor(0.0, 0.0, 0.0, 0.0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      const canvas = document.getElementById('webgl-canvas');
      const aspect = canvas.width / canvas.height;
      const pMat = mat4Perspective(mat4Create(), 45 * Math.PI / 180, aspect, maxDim * 0.05, maxDim * 20);

      const eyeX = target[0] + radius * Math.sin(phi) * Math.sin(theta);
      const eyeY = target[1] + radius * Math.cos(phi);
      const eyeZ = target[2] + radius * Math.sin(phi) * Math.cos(theta);
      const vMat = mat4LookAt(mat4Create(), [eyeX, eyeY, eyeZ], target, [0, 1, 0]);

      const mvp = mat4Multiply(mat4Create(), pMat, vMat);
      const normMat = mat3NormalFromMat4(new Float32Array(9), vMat);

      // Adapt colors to host theme
      const isLight = document.documentElement.classList.contains('light');
      const meshColor = isLight ? [0.65, 0.72, 0.82] : [0.42, 0.52, 0.65];
      const lineColor = isLight ? [0.10, 0.14, 0.22, 0.95] : [0.06, 0.09, 0.15, 0.95];

      // Draw Faces
      gl.useProgram(faceProg);
      gl.uniformMatrix4fv(gl.getUniformLocation(faceProg, "uMVP"), false, mvp);
      gl.uniformMatrix4fv(gl.getUniformLocation(faceProg, "uMV"), false, vMat);
      gl.uniformMatrix3fv(gl.getUniformLocation(faceProg, "uNormMat"), false, normMat);

      gl.uniform3f(gl.getUniformLocation(faceProg, "uColor"), meshColor[0], meshColor[1], meshColor[2]);
      gl.uniform3f(gl.getUniformLocation(faceProg, "uLight1"), 1.0, 1.8, 1.2);
      gl.uniform3f(gl.getUniformLocation(faceProg, "uLight2"), -1.0, -0.8, -1.0);
      gl.uniform1f(gl.getUniformLocation(faceProg, "uAmbient"), isLight ? 0.42 : 0.35);

      const aPos = gl.getAttribLocation(faceProg, "aPos");
      gl.enableVertexAttribArray(aPos);
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);

      const aNorm = gl.getAttribLocation(faceProg, "aNorm");
      gl.enableVertexAttribArray(aNorm);
      gl.bindBuffer(gl.ARRAY_BUFFER, normBuffer);
      gl.vertexAttribPointer(aNorm, 3, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);

      // Enable polygon offset for faces to give depth buffer precedence to lines
      gl.enable(gl.POLYGON_OFFSET_FILL);
      gl.polygonOffset(1.0, 1.0);
      gl.drawElements(gl.TRIANGLES, indexCount, indexType, 0);
      gl.disable(gl.POLYGON_OFFSET_FILL);

      // Draw CAD Feature Edges
      if (showEdges && edgeBuffer && edgeCount > 0) {
        gl.useProgram(lineProg);
        gl.uniformMatrix4fv(gl.getUniformLocation(lineProg, "uMVP"), false, mvp);
        gl.uniform4f(gl.getUniformLocation(lineProg, "uLineColor"), lineColor[0], lineColor[1], lineColor[2], lineColor[3]);

        const aLinePos = gl.getAttribLocation(lineProg, "aPos");
        gl.enableVertexAttribArray(aLinePos);
        gl.bindBuffer(gl.ARRAY_BUFFER, edgeBuffer);
        gl.vertexAttribPointer(aLinePos, 3, gl.FLOAT, false, 0, 0);

        gl.drawArrays(gl.LINES, 0, edgeCount);
      }

      requestAnimationFrame(render);
    }

    function setupInteraction(canvas) {
      let isDragging = false;
      let dragMode = "orbit"; // "orbit" or "pan"
      let lastX = 0, lastY = 0;

      canvas.addEventListener("mousedown", (e) => {
        isDragging = true;
        dragMode = (e.button === 2 || e.shiftKey) ? "pan" : "orbit";
        lastX = e.clientX;
        lastY = e.clientY;
      });

      window.addEventListener("mouseup", () => { isDragging = false; });
      canvas.addEventListener("contextmenu", (e) => e.preventDefault());

      window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        lastX = e.clientX;
        lastY = e.clientY;

        if (dragMode === "orbit") {
          theta -= dx * 0.008;
          phi -= dy * 0.008;
          phi = Math.max(0.05, Math.min(Math.PI - 0.05, phi));
        } else {
          // Pan in view plane
          const panSpeed = radius * 0.0015;
          const cosT = Math.cos(theta), sinT = Math.sin(theta);
          target[0] += (-dx * cosT) * panSpeed;
          target[2] += (dx * sinT) * panSpeed;
          target[1] += dy * panSpeed;
        }
      });

      canvas.addEventListener("wheel", (e) => {
        e.preventDefault();
        radius *= (e.deltaY > 0 ? 1.08 : 0.92);
        radius = Math.max(maxDim * 0.2, Math.min(maxDim * 8.0, radius));
      }, { passive: false });

      // Touch events
      let touchDist = 0;
      canvas.addEventListener("touchstart", (e) => {
        if (e.touches.length === 1) {
          isDragging = true;
          dragMode = "orbit";
          lastX = e.touches[0].clientX;
          lastY = e.touches[0].clientY;
        } else if (e.touches.length === 2) {
          isDragging = false;
          touchDist = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
        }
      });

      canvas.addEventListener("touchmove", (e) => {
        if (e.touches.length === 1 && isDragging) {
          const dx = e.touches[0].clientX - lastX;
          const dy = e.touches[0].clientY - lastY;
          lastX = e.touches[0].clientX;
          lastY = e.touches[0].clientY;
          theta -= dx * 0.008;
          phi -= dy * 0.008;
          phi = Math.max(0.05, Math.min(Math.PI - 0.05, phi));
        } else if (e.touches.length === 2) {
          const dist = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
          if (touchDist > 0) {
            const factor = touchDist / dist;
            radius *= (factor > 1 ? 1.04 : 0.96);
            radius = Math.max(maxDim * 0.2, Math.min(maxDim * 8.0, radius));
          }
          touchDist = dist;
        }
      });

      canvas.addEventListener("touchend", () => { isDragging = false; touchDist = 0; });

      // Buttons
      document.getElementById("btn-reset").addEventListener("click", () => {
        target = [0, 0, 0];
        radius = defaultRadius;
        theta = Math.PI / 4;
        phi = Math.PI / 3;
      });

      document.getElementById("btn-edges").addEventListener("click", (e) => {
        showEdges = !showEdges;
        e.target.style.opacity = showEdges ? "1.0" : "0.5";
      });

      document.getElementById("btn-rotate").addEventListener("click", (e) => {
        autoRotate = !autoRotate;
        e.target.style.color = autoRotate ? "var(--primary)" : "var(--foreground)";
      });
    }

    window.addEventListener("DOMContentLoaded", initWebGL);
  </script>
</body>
</html>
"""


def export_viewer_html(
    object_name=None,
    document_name=None,
    output_path=None,
    linear_deflection=0.3,
    title=None,
    mode="chat",
):
    """Export 3D object to a self-contained, zero-dependency interactive WebGL HTML viewer.

    Parameters:
    - object_name: Optional target object name (defaults to active object or first Body).
    - document_name: Optional FreeCAD document name.
    - output_path: Optional destination .html file path.
    - linear_deflection: Mesh tessellation chordal deflection in mm (default 0.3).
    - title: Optional viewer window title.
    - mode: "chat" (compact inline embed card < 450px) or "standalone" (fullscreen).
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = None
    if object_name:
        obj = doc.getObject(object_name)
    else:
        obj = getattr(doc, "ActiveObject", None)
        if not obj:
            for o in doc.Objects:
                if hasattr(o, "Shape") and not o.Shape.isNull():
                    obj = o
                    break

    if not obj:
        return {"error": "No valid 3D object found to export to 3D HTML."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{obj.Name}' has no valid Shape."}

    # Tessellate shape to faces
    lin_defl = max(0.05, float(linear_deflection))
    pts, tris = shape.tessellate(lin_defl)
    bb = shape.BoundBox

    # Center of bounding box
    cx, cy, cz = bb.Center.x, bb.Center.y, bb.Center.z

    # Transform coordinates from FreeCAD (X right, Y back, Z up) to WebGL (X right, Y up, Z front):
    # (x, y, z) -> (x - cx, z - cz, -(y - cy))
    flat_verts = []
    for p in pts:
        flat_verts.extend([round(p.x - cx, 3), round(p.z - cz, 3), round(-(p.y - cy), 3)])

    flat_indices = []
    for t in tris:
        flat_indices.extend([t[0], t[1], t[2]])

    # Compute smoothed vertex normals in WebGL coordinates
    normals = [[0.0, 0.0, 0.0] for _ in pts]
    for t in tris:
        p0 = pts[t[0]]
        p1 = pts[t[1]]
        p2 = pts[t[2]]
        v1 = p1 - p0
        v2 = p2 - p0
        fn = v1.cross(v2)
        l = fn.Length
        if l > 1e-6:
            fn = fn * (1.0 / l)
            for idx in t:
                normals[idx][0] += fn.x
                normals[idx][1] += fn.y
                normals[idx][2] += fn.z

    flat_normals = []
    for n in normals:
        l = math.hypot(n[0], n[1], n[2])
        if l > 1e-6:
            flat_normals.extend([round(n[0] / l, 3), round(n[2] / l, 3), round(-n[1] / l, 3)])
        else:
            flat_normals.extend([0.0, 1.0, 0.0])

    # Discretize authentic CAD feature edges (no triangle diagonals!)
    flat_edges = []
    edge_seg_count = 0
    max_edge_segs = 12000
    for e in shape.Edges:
        if edge_seg_count >= max_edge_segs:
            break
        try:
            e_pts = e.discretize(Deflection=max(lin_defl * 1.5, 0.2))
            for i in range(len(e_pts) - 1):
                p_a = e_pts[i]
                p_b = e_pts[i + 1]
                flat_edges.extend([
                    round(p_a.x - cx, 3), round(p_a.z - cz, 3), round(-(p_a.y - cy), 3),
                    round(p_b.x - cx, 3), round(p_b.z - cz, 3), round(-(p_b.y - cy), 3),
                ])
                edge_seg_count += 1
                if edge_seg_count >= max_edge_segs:
                    break
        except Exception:
            pass

    model_title = title or f"{doc.Name} - {getattr(obj, 'Label', obj.Name)}"

    mesh_payload = {
        "title": model_title,
        "objectName": obj.Name,
        "documentName": doc.Name,
        "dimensions": {
            "x": round(bb.XLength, 2),
            "y": round(bb.YLength, 2),
            "z": round(bb.ZLength, 2),
        },
        "bboxCenter": [0.0, 0.0, 0.0],
        "vertices": flat_verts,
        "normals": flat_normals,
        "indices": flat_indices,
        "edges": flat_edges,
        "stats": {
            "verticesCount": len(pts),
            "trianglesCount": len(tris),
            "edgesCount": edge_seg_count,
            "facesCount": len(shape.Faces),
        },
    }

    render_mode = "chat" if (mode or "chat").lower().strip() == "chat" else "standalone"
    html_content = _build_html_template(mesh_payload, render_mode)

    # Determine destination path
    if not output_path:
        export_dir = os.path.join(FreeCAD.getUserAppDataDir(), "mcp_exports")
        os.makedirs(export_dir, exist_ok=True)
        suffix = "chat_viewer" if render_mode == "chat" else "standalone_viewer"
        output_path = os.path.join(export_dir, f"{doc.Name}_{obj.Name}_{suffix}.html")
    else:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "status": "ok",
        "document": doc.Name,
        "object": obj.Name,
        "mode": render_mode,
        "output_path": output_path,
        "embed_tag": f'<agent-embed src="file://{output_path}"></agent-embed>',
        "file_size_bytes": os.path.getsize(output_path),
        "vertices_count": len(pts),
        "triangles_count": len(tris),
        "edges_count": edge_seg_count,
        "dimensions_mm": [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
    }


def _build_html_template(data, mode="chat"):
    json_str = json.dumps(data)
    is_chat = (mode == "chat")

    body_class = "bg-transparent text-[var(--foreground)] antialiased p-2 m-0 overflow-hidden" if is_chat else "bg-[var(--background)] text-[var(--foreground)] antialiased m-0 overflow-hidden w-screen h-screen"
    container_class = (
        "bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-3 shadow-md max-w-2xl mx-auto"
        if is_chat else "w-full h-full relative"
    )
    canvas_wrapper_class = (
        "relative w-full h-[320px] rounded-lg overflow-hidden bg-slate-900/10 dark:bg-black/40 border border-[var(--border)]"
        if is_chat else "w-full h-full relative bg-slate-950"
    )

    dims = f"{data['dimensions']['x']}×{data['dimensions']['y']}×{data['dimensions']['z']}"
    tris = f"{data['stats']['trianglesCount']:,}"
    doc_info = f"{data.get('documentName', '')} / {data.get('objectName', '')}"

    html = HTML_TEMPLATE
    html = html.replace("__TITLE__", data.get("title", "CAD Model"))
    html = html.replace("__DOC_INFO__", doc_info)
    html = html.replace("__DIMS__", dims)
    html = html.replace("__TRIS__", tris)
    html = html.replace("__BODY_CLASS__", body_class)
    html = html.replace("__CONTAINER_CLASS__", container_class)
    html = html.replace("__CANVAS_WRAPPER_CLASS__", canvas_wrapper_class)
    html = html.replace("__JSON_DATA__", json_str)
    return html


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
