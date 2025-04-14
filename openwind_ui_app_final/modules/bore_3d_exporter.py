
import cadquery as cq
from tempfile import NamedTemporaryFile

def generate_bore_model(bore_df, wall_thickness=2.0, length_scale=1.0):
    scaled_pos = bore_df["position"] * length_scale
    radii = bore_df["diameter"] / 2
    path_pts = [(0, 0, z) for z in scaled_pos]
    shell = cq.Workplane("XY").spline(path_pts).sweep(cq.Workplane("XY").circle(radii.iloc[0] * 1000 + wall_thickness))
    return shell

def export_model_as_stl(workpiece, filename="bore_model.stl"):
    tmp_file = NamedTemporaryFile(delete=False, suffix=".stl")
    workpiece.val().exportStl(tmp_file.name)
    with open(tmp_file.name, "rb") as f:
        return f.read(), tmp_file.name

def export_model_as_step(workpiece, filename="bore_model.step"):
    tmp_file = NamedTemporaryFile(delete=False, suffix=".step")
    workpiece.val().exportStep(tmp_file.name)
    with open(tmp_file.name, "rb") as f:
        return f.read(), tmp_file.name
