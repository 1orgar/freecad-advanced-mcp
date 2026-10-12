"""Standalone WebGL/Three.js 3D HTML viewer exporter for FreeCAD MCP."""

import os
import json
import FreeCAD


def export_viewer_html(
    object_name=None,
    document_name=None,
    output_path=None,
    linear_deflection=0.3,
    title=None,
):
    """Export 3D object to a self-contained interactive WebGL HTML viewer with OrbitControls.

    Parameters:
    - object_name: Optional target object name (defaults to active object or first Body).
    - document_name: Optional FreeCAD document name.
    - output_path: Optional destination .html file path.
    - linear_deflection: Mesh tessellation chordal deflection in mm (default 0.3).
    - title: Optional viewer window title.
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
            # Fallback to first PartDesign Body or Shape object
            for o in doc.Objects:
                if hasattr(o, "Shape") and not o.Shape.isNull():
                    obj = o
                    break

    if not obj:
        return {"error": "No valid 3D object found to export to 3D HTML."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{obj.Name}' has no valid Shape."}

    # Tessellate shape
    pts, tris = shape.tessellate(float(linear_deflection))
    bb = shape.BoundBox

    # Flatten vertices and triangles
    flat_verts = []
    for p in pts:
        flat_verts.extend([round(p.x, 3), round(p.y, 3), round(p.z, 3)])

    flat_indices = []
    for t in tris:
        flat_indices.extend([t[0], t[1], t[2]])

    model_title = title or f"{doc.Name} - {obj.Label or obj.Name}"

    mesh_payload = {
        "title": model_title,
        "objectName": obj.Name,
        "documentName": doc.Name,
        "dimensions": {
            "x": round(bb.XLength, 2),
            "y": round(bb.YLength, 2),
            "z": round(bb.ZLength, 2),
        },
        "bboxCenter": [round(bb.Center.x, 3), round(bb.Center.y, 3), round(bb.Center.z, 3)],
        "vertices": flat_verts,
        "indices": flat_indices,
        "stats": {
            "verticesCount": len(pts),
            "trianglesCount": len(tris),
            "facesCount": len(shape.Faces),
        },
    }

    html_content = _build_html_template(mesh_payload)

    # Determine destination path
    if not output_path:
        export_dir = os.path.join(FreeCAD.getUserAppDataDir(), "mcp_exports")
        os.makedirs(export_dir, exist_ok=True)
        output_path = os.path.join(export_dir, f"{doc.Name}_{obj.Name}_3d_viewer.html")
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
        "output_path": output_path,
        "file_size_bytes": os.path.getsize(output_path),
        "vertices_count": len(pts),
        "triangles_count": len(tris),
        "dimensions_mm": [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
    }


def _build_html_template(data):
    json_str = json.dumps(data)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data['title']}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #1e1e24;
      color: #f0f0f5;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
    }}
    #canvas-container {{ width: 100%; height: 100%; display: block; }}
    .hud-panel {{
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(30, 30, 36, 0.82);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      padding: 16px 20px;
      max-width: 320px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
      pointer-events: auto;
      z-index: 10;
    }}
    .hud-title {{ font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 6px; }}
    .hud-subtitle {{ font-size: 12px; color: #9a9ab0; margin-bottom: 12px; }}
    .hud-metric {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      padding: 4px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .hud-metric span:first-child {{ color: #a0a0b8; }}
    .hud-metric span:last-child {{ font-weight: 600; color: #38bdf8; font-variant-numeric: tabular-nums; }}
    .hud-controls {{
      position: absolute;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      gap: 10px;
      background: rgba(30, 30, 36, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 30px;
      padding: 8px 14px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4);
      z-index: 10;
    }}
    button.btn {{
      background: rgba(255, 255, 255, 0.08);
      color: #e2e8f0;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    button.btn:hover {{
      background: #38bdf8;
      color: #0f172a;
      border-color: #38bdf8;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div class="hud-panel">
    <div class="hud-title">{data['title']}</div>
    <div class="hud-subtitle">Doc: {data['documentName']} | Object: {data['objectName']}</div>
    <div class="hud-metric"><span>Dimensions:</span><span>{data['dimensions']['x']} x {data['dimensions']['y']} x {data['dimensions']['z']} mm</span></div>
    <div class="hud-metric"><span>Triangles:</span><span>{data['stats']['trianglesCount']:,}</span></div>
    <div class="hud-metric"><span>Vertices:</span><span>{data['stats']['verticesCount']:,}</span></div>
    <div class="hud-metric"><span>Faces:</span><span>{data['stats']['facesCount']}</span></div>
  </div>

  <div class="hud-controls">
    <button class="btn" onclick="resetCamera()">Reset View</button>
    <button class="btn" onclick="toggleEdges()">Edges</button>
    <button class="btn" onclick="toggleTheme()">Theme</button>
  </div>

  <div id="canvas-container"></div>

  <script>
    const MODEL = {json_str};

    let scene, camera, renderer, controls, meshGroup, edgesLine;
    let showEdges = true;
    let darkTheme = true;

    function init() {{
      const container = document.getElementById('canvas-container');
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x1e1e24);

      camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 2000);
      
      renderer = new THREE.WebGLRenderer({{ antialias: true }});
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.shadowMap.enabled = true;
      container.appendChild(renderer.domElement);

      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;

      // Lights
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
      scene.add(ambientLight);

      const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.9);
      dirLight1.position.set(200, 300, 200);
      scene.add(dirLight1);

      const dirLight2 = new THREE.DirectionalLight(0x90cdf4, 0.4);
      dirLight2.position.set(-200, -200, -200);
      scene.add(dirLight2);

      // Build Geometry
      const geometry = new THREE.BufferGeometry();
      const posArray = new Float32Array(MODEL.vertices);
      geometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
      geometry.setIndex(MODEL.indices);
      geometry.computeVertexNormals();

      // Material
      const material = new THREE.MeshStandardMaterial({{
        color: 0x8892b0,
        roughness: 0.35,
        metalness: 0.15,
        flatShading: true,
        side: THREE.DoubleSide
      }});

      meshGroup = new THREE.Group();
      const mesh = new THREE.Mesh(geometry, material);
      meshGroup.add(mesh);

      // Edges
      const edgesGeo = new THREE.EdgesGeometry(geometry, 25);
      edgesLine = new THREE.LineSegments(edgesGeo, new THREE.LineBasicMaterial({{ color: 0x111827, linewidth: 1 }}));
      meshGroup.add(edgesLine);

      // Center model
      const cx = MODEL.bboxCenter[0];
      const cy = MODEL.bboxCenter[1];
      const cz = MODEL.bboxCenter[2];
      meshGroup.position.set(-cx, -cy, -cz);

      // Adjust coordinate frame: FreeCAD Z is usually up, in Three.js Y is up
      meshGroup.rotation.x = -Math.PI / 2;

      scene.add(meshGroup);

      // Camera positioning
      const maxDim = Math.max(MODEL.dimensions.x, MODEL.dimensions.y, MODEL.dimensions.z);
      camera.position.set(maxDim * 1.5, maxDim * 1.2, maxDim * 1.8);
      controls.target.set(0, 0, 0);
      controls.update();

      // Grid helper
      const grid = new THREE.GridHelper(maxDim * 2.5, 20, 0x3b82f6, 0x334155);
      grid.position.y = - (MODEL.dimensions.z / 2);
      scene.add(grid);

      window.addEventListener('resize', onWindowResize);
      animate();
    }}

    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}

    function onWindowResize() {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }}

    function resetCamera() {{
      const maxDim = Math.max(MODEL.dimensions.x, MODEL.dimensions.y, MODEL.dimensions.z);
      camera.position.set(maxDim * 1.5, maxDim * 1.2, maxDim * 1.8);
      controls.target.set(0, 0, 0);
      controls.update();
    }}

    function toggleEdges() {{
      showEdges = !showEdges;
      if (edgesLine) edgesLine.visible = showEdges;
    }}

    function toggleTheme() {{
      darkTheme = !darkTheme;
      scene.background = new THREE.Color(darkTheme ? 0x1e1e24 : 0xf1f5f9);
      if (edgesLine) {{
        edgesLine.material.color = new THREE.Color(darkTheme ? 0x111827 : 0x475569);
      }}
    }}

    window.onload = init;
  </script>
</body>
</html>
"""


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
