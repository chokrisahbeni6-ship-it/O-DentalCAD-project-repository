"""Fabrique un jeu de données 100 % SYNTHÉTIQUE (aucun patient) dans /tmp/testdata :
 - dicom/        : faux CBCT (une arcade en "fer à cheval")
 - scan.stl      : surface de cette arcade, légèrement déplacée (pour tester le calage)
 - gencive.stl   : gabarit de gencive (pour tester le guide)
Usage : docker compose exec backend python -m app.make_test_data
Puis  : docker compose cp backend:/tmp/testdata ./testdata
"""
import os

import numpy as np
import SimpleITK as sitk
import trimesh

from app.segmentation import _export_mask_to_stl

OUT = "/tmp/testdata"
SP = 0.3                                   # mm par voxel
NX, NY, NZ = 200, 200, 120
ORIGIN = (-NX * SP / 2, -NY * SP / 2, -NZ * SP / 2)


def main():
    os.makedirs(os.path.join(OUT, "dicom"), exist_ok=True)
    x = ORIGIN[0] + np.arange(NX) * SP
    y = ORIGIN[1] + np.arange(NY) * SP
    z = ORIGIN[2] + np.arange(NZ) * SP
    Z, Y, X = np.meshgrid(z, y, x, indexing="ij")          # (z, y, x)
    r_out = (X / 26.0) ** 2 + (Y / 22.0) ** 2 <= 1
    r_in = (X / 16.0) ** 2 + (Y / 12.0) ** 2 <= 1
    ring = r_out & ~r_in & (Y > -6)                         # fer à cheval ouvert vers l'arrière
    bone = ring & (Z >= -8) & (Z <= 6)
    vol = np.where(bone, 1200, 0).astype(np.int16)
    vol += np.random.default_rng(0).integers(-20, 20, vol.shape).astype(np.int16)

    img = sitk.GetImageFromArray(vol)
    img.SetSpacing((SP, SP, SP))
    img.SetOrigin(ORIGIN)

    uid_root = "1.2.826.0.1.3680043.8.498."
    rng = np.random.default_rng(1)
    study = uid_root + str(int(rng.integers(10**9, 10**10)))
    series = study + ".1"
    writer = sitk.ImageFileWriter()
    writer.KeepOriginalImageUIDOn()
    for k in range(NZ):
        sl = img[:, :, k]
        zk = ORIGIN[2] + k * SP
        tags = {
            "0008|0016": "1.2.840.10008.5.1.4.1.1.2", "0008|0018": f"{series}.{k + 1}",
            "0008|0060": "CT", "0010|0010": "TEST^SYNTHETIQUE", "0010|0020": "TEST-0001",
            "0020|000d": study, "0020|000e": series, "0020|0013": str(k + 1),
            "0020|0032": f"{ORIGIN[0]}\\{ORIGIN[1]}\\{zk}", "0020|0037": "1\\0\\0\\0\\1\\0",
            "0028|0030": f"{SP}\\{SP}", "0018|0050": str(SP),
            "0028|1052": "0", "0028|1053": "1",
        }
        for tag, val in tags.items():
            sl.SetMetaData(tag, val)
        writer.SetFileName(os.path.join(OUT, "dicom", f"slice_{k:04d}.dcm"))
        writer.Execute(sl)

    # STL de l'arcade, puis déplacement connu (5° autour de Z, +3 mm en X, -2 mm en Y)
    ref = img
    raw = os.path.join(OUT, "_arcade.stl")
    _export_mask_to_stl(bone.astype(np.uint8), ref, raw)
    mesh = trimesh.load(raw, force="mesh")
    T = trimesh.transformations.rotation_matrix(np.deg2rad(5), [0, 0, 1])
    T[:3, 3] = [3.0, -2.0, 0.0]
    mesh.apply_transform(T)
    mesh.export(os.path.join(OUT, "scan.stl"))
    os.remove(raw)

    gum = trimesh.creation.box(extents=[30, 12, 2])
    gum.apply_translation([-7, 16, 5])                     # sommet à z = 6
    gum.export(os.path.join(OUT, "gencive.stl"))
    print("Jeu de test créé dans", OUT)


if __name__ == "__main__":
    main()
