print("Hello RocScript")

"""
F#256 OPEN PIT SLOPE
RS3 4.043 ROCSCRIPT AUTOMATION

Workflow:
1. Validate input files
2. Connect to the running RS3 scripting server
3. Open the prepared template
4. Import the DXF surface
5. Save immediately as F256_DISP.rs3
6. Pause for topography verification
7. Pause for manual block-model import
8. Pause for manual 10 m mesh-size setting
9. Generate the mesh
10. Compute the displacement model
11. Pause for manual result export
12. Copy the displacement model to F256_SRF.rs3
13. Pause for manual SRF activation
14. Compute SRF
15. Export SRF trial convergence history

Important:
- The RS3 scripting server must already be running on port 60064.
- F256_Template.rs3 must be prepared before running this script.
- Block-model import, global mesh size, and SRF activation remain manual.
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

from rs3.RS3Modeler import RS3Modeler
from rs3.mesh.MeshEnums import MeshElementType, MeshGradation


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Project paths and settings."""

    PROJECT_BASE = Path(
        r"C:\Users\GTUW2578\OneDrive - Amman Mineral\George"
        r"\03. Project\01. Analysis\2026\17. F#256"
    )

    MATERIAL_PATH = PROJECT_BASE / "03. Material"
    OUTPUT_PATH = PROJECT_BASE / "01. Analysis"

    # Prepared RS3 template
    TEMPLATE_MODEL = OUTPUT_PATH / "F256_Template.rs3"

    # Input files
    SURFACE_DXF = MATERIAL_PATH / "261007_Surf.dxf"
    BLOCK_MODEL_CSV = MATERIAL_PATH / "261008_BM RS3.csv"

    # Output models
    DISP_MODEL = OUTPUT_PATH / "F256_DISP.rs3"
    SRF_MODEL = OUTPUT_PATH / "F256_SRF.rs3"

    # Result files
    SRF_SUMMARY = OUTPUT_PATH / "F256_SRF_Convergence_History.txt"

    # RS3 scripting server
    RS3_PORT = 60064

    # Final mesh size is set manually in RS3
    FINAL_MESH_SIZE = 10.0

    # For the first trial, consider using 25 m
    TEST_MESH_SIZE = 25.0


# =============================================================================
# LOGGING
# =============================================================================

def log(level, message):
    """Print a timestamped message."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level:8s}] {message}")


def log_step(number, title):
    """Print a workflow step heading."""

    print()
    print("=" * 80)
    print(f"STEP {number}: {title}")
    print("=" * 80)


def pause(message="Press ENTER to continue..."):
    """Pause execution until the user presses Enter."""

    print()
    input(message)


# =============================================================================
# STEP 1: VALIDATE INPUTS
# =============================================================================

def validate_inputs():
    """Verify that all required files and directories exist."""

    log_step(1, "VALIDATE INPUT FILES")

    Config.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    required_files = {
        "RS3 template": Config.TEMPLATE_MODEL,
        "DXF surface": Config.SURFACE_DXF,
        "Block-model CSV": Config.BLOCK_MODEL_CSV,
    }

    missing_files = []

    for description, file_path in required_files.items():
        if file_path.exists():
            log("OK", f"{description}: {file_path}")
        else:
            log("ERROR", f"{description} not found: {file_path}")
            missing_files.append(file_path)

    if missing_files:
        print()
        log("ACTION", "Prepare the missing files before running the script.")

        if Config.TEMPLATE_MODEL in missing_files:
            print_template_requirements()

        raise FileNotFoundError(
            "One or more required input files could not be found."
        )

    log("OK", f"Analysis output folder: {Config.OUTPUT_PATH}")


def print_template_requirements():
    """Print the required settings for F256_Template.rs3."""

    print()
    log("ACTION", "Create F256_Template.rs3 manually with these settings:")
    print()

    log("ACTION", "Model boundaries:")
    log("ACTION", "  X minimum = 5320 m")
    log("ACTION", "  X maximum = 6280 m")
    log("ACTION", "  Y minimum = 9420 m")
    log("ACTION", "  Y maximum = 10680 m")
    log("ACTION", "  Bottom elevation = -300 m")
    log("ACTION", "  Upper boundary must accommodate the topography")
    print()

    log("ACTION", "Project settings:")
    log("ACTION", "  Units = Metric")
    log("ACTION", "  Stress unit = MPa")
    log("ACTION", "  Small strain = ON")
    log("ACTION", "  Groundwater = OFF")
    log("ACTION", "  Gravity loading = ON")
    log("ACTION", "  Field stress or K0 = OFF")
    log("ACTION", "  One analysis stage")
    print()

    log("ACTION", "Boundary restraints:")
    log("ACTION", "  Bottom = X, Y, and Z restrained")
    log("ACTION", "  X-min and X-max sides = X restrained")
    log("ACTION", "  Y-min and Y-max sides = Y restrained")
    log("ACTION", "  Topographic surface = free")
    print()

    log("ACTION", "Materials:")
    log("ACTION", "  Vx = Generalized Hoek-Brown")
    log("ACTION", "    Unit weight = 27 kN/m3")
    log("ACTION", "    Poisson ratio = 0.25")
    print()

    log("ACTION", "  Dio = Generalized Hoek-Brown")
    log("ACTION", "    Unit weight = 27 kN/m3")
    log("ACTION", "    Poisson ratio = 0.22")
    print()

    log("ACTION", "  Fill = Mohr-Coulomb, perfect plasticity")
    log("ACTION", "    Unit weight = 21 kN/m3")
    log("ACTION", "    Peak cohesion = 0.005 MPa")
    log("ACTION", "    Peak friction angle = 35 degrees")
    log("ACTION", "    Residual cohesion = 0.005 MPa")
    log("ACTION", "    Residual friction angle = 35 degrees")
    print()

    log("ACTION", f"Save the template as: {Config.TEMPLATE_MODEL}")


# =============================================================================
# STEP 2: CONNECT TO RS3
# =============================================================================

def connect_to_rs3():
    """Connect to an already running RS3 scripting server."""

    log_step(2, "CONNECT TO RS3")

    log(
        "INFO",
        f"Connecting to the RS3 scripting server on port {Config.RS3_PORT}..."
    )

    try:
        modeler = RS3Modeler(Config.RS3_PORT)
    except Exception as error:
        log("ERROR", f"Could not connect to RS3: {error}")
        print()
        log("ACTION", "Open RS3.")
        log("ACTION", "Open Scripting > Manage Scripting Server.")
        log("ACTION", f"Start the server on port {Config.RS3_PORT}.")
        raise

    log("OK", "Connected to RS3")
    return modeler


# =============================================================================
# STEP 3: OPEN TEMPLATE
# =============================================================================

def open_template(modeler):
    """Open the prepared RS3 template."""

    log_step(3, "OPEN TEMPLATE MODEL")

    log("INFO", f"Opening template: {Config.TEMPLATE_MODEL.name}")

    try:
        model = modeler.openFile(str(Config.TEMPLATE_MODEL))
    except Exception as error:
        log("ERROR", f"Could not open the template: {error}")
        raise

    log("OK", "Template model opened")
    return model


# =============================================================================
# STEP 4: IMPORT DXF
# =============================================================================

def import_dxf_surface(model):
    """Import the DXF topographic surface."""

    log_step(4, "IMPORT DXF SURFACE")

    log("INFO", f"Importing: {Config.SURFACE_DXF}")

    try:
        model.Geometry.importGeometry(str(Config.SURFACE_DXF))
    except Exception as error:
        log("ERROR", f"DXF import failed: {error}")
        raise

    log("OK", "DXF geometry imported")


# =============================================================================
# STEP 5: SAVE WORKING DISPLACEMENT MODEL
# =============================================================================

def save_displacement_model(model):
    """
    Save the working model immediately so that the original template remains
    unchanged.
    """

    log_step(5, "SAVE WORKING DISPLACEMENT MODEL")

    if Config.DISP_MODEL.exists():
        log(
            "WARNING",
            f"Existing file will be overwritten or updated: "
            f"{Config.DISP_MODEL.name}"
        )

    log("INFO", f"Saving working model as: {Config.DISP_MODEL.name}")

    try:
        model.saveAs(str(Config.DISP_MODEL))
    except Exception as error:
        log("ERROR", f"Could not save the displacement model: {error}")
        raise

    log("OK", f"Working model saved: {Config.DISP_MODEL}")


# =============================================================================
# STEP 6: VERIFY TOPOGRAPHY
# =============================================================================

def manual_surface_check_pause():
    """Pause while the user verifies the topographic geometry."""

    log_step(6, "MANUAL STEP: VERIFY TOPOGRAPHIC SURFACE")

    log("WARNING", "Importing the DXF does not necessarily trim the volume.")
    print()

    log("ACTION", "In the open F256_DISP model, verify the following:")
    log("ACTION", "  1. The DXF surface is in the correct coordinates.")
    log("ACTION", "  2. The surface intersects the external volume.")
    log("ACTION", "  3. Divide or trim the external volume using the surface.")
    log("ACTION", "  4. Remove or deactivate the portion above the surface.")
    log("ACTION", "  5. Keep the model material only below the surface.")
    log("ACTION", "  6. Confirm the bottom elevation is -300 m.")
    log("ACTION", "  7. Save the model using File > Save.")

    pause("Press ENTER after the topography has been checked and saved...")

    log("OK", "Topography verification acknowledged")


# =============================================================================
# STEP 7: MANUAL BLOCK-MODEL IMPORT
# =============================================================================

def manual_block_model_import_pause():
    """Pause while the block model is imported using the RS3 interface."""

    log_step(7, "MANUAL STEP: IMPORT BLOCK MODEL")

    log(
        "WARNING",
        "Block-model CSV import is not automated by this script."
    )

    print()
    log("ACTION", "In the open F256_DISP model:")
    log("ACTION", "  1. Open Materials > Import Block Model.")
    log("ACTION", f"  2. Select CSV: {Config.BLOCK_MODEL_CSV}")
    print()

    log("ACTION", "Coordinate mapping:")
    log("ACTION", "  X coordinate = EAST")
    log("ACTION", "  Y coordinate = NORTH")
    log("ACTION", "  Z coordinate = ELEV")
    log("ACTION", "  Lithology/material field = Lit Interpret")
    log("ACTION", "  First data row = row 2")
    print()

    log("ACTION", "Block dimensions:")
    log("ACTION", "  X dimension = 25 m")
    log("ACTION", "  Y dimension = 25 m")
    log("ACTION", "  Z dimension = 15 m")
    print()

    log("ACTION", "Hoek-Brown field mapping:")
    log("ACTION", "  GSI = GSI")
    log("ACTION", "  Intact rock constant = Mi")
    log("ACTION", "  Disturbance factor = D2")
    log("ACTION", "  UCS = UCS")
    log("ACTION", "  Young's modulus = E (MPa)")
    print()

    log("ACTION", "Required lithology mapping:")
    log("ACTION", "  Vx must map to Vx")
    log("ACTION", "  Dio must map to Dio")
    log("ACTION", "  Every other lithology must map to Fill")
    print()

    log("WARNING", "Do not assume other lithologies automatically become Fill.")
    log(
        "ACTION",
        "Confirm the material mapping in the import wizard or block-model setup."
    )
    print()

    log("ACTION", "After import:")
    log("ACTION", "  1. Assign the imported block-model property to the volume.")
    log("ACTION", "  2. Inspect representative Vx blocks.")
    log("ACTION", "  3. Inspect representative Dio blocks.")
    log("ACTION", "  4. Inspect representative Fill blocks.")
    log("ACTION", "  5. Confirm GSI, Mi, D2, UCS, and E values.")
    log("ACTION", "  6. Save the model using File > Save.")

    pause("Press ENTER after the block model has been imported and checked...")

    log("OK", "Block-model import acknowledged")


# =============================================================================
# STEP 8: SET MESH SIZE
# =============================================================================

def manual_mesh_size_pause():
    """Pause while the global mesh size is set manually."""

    log_step(8, "MANUAL STEP: SET GLOBAL MESH SIZE")

    log("ACTION", "In RS3, open Mesh > Mesh Settings.")
    print()

    log(
        "ACTION",
        f"For the final analysis, set global mesh size to "
        f"{Config.FINAL_MESH_SIZE:.0f} m."
    )
    log("ACTION", "Element type = 10-Noded Tetrahedra")
    log("ACTION", "Mesh gradation = Uniform")
    print()

    log(
        "RECOMMEND",
        f"For the first test, use {Config.TEST_MESH_SIZE:.0f} m."
    )
    log(
        "RECOMMEND",
        "Change to 10 m only after geometry and material mapping are verified."
    )
    print()

    log("ACTION", "Click OK, but do not generate the mesh manually.")
    log("ACTION", "Save the model using File > Save.")

    pause("Press ENTER after the mesh size has been set and saved...")

    log("OK", "Mesh-setting configuration acknowledged")


# =============================================================================
# STEP 9: GENERATE MESH
# =============================================================================

def generate_mesh(model):
    """Configure the verified mesh options and generate the mesh."""

    log_step(9, "GENERATE MESH")

    mesh = model.Mesh

    log("INFO", "Setting element type to 10-noded tetrahedra...")

    try:
        mesh.setElementType(
            MeshElementType.MESH_10_NODED_TETRAHEDRA
        )
    except Exception as error:
        log("ERROR", f"Could not set the element type: {error}")
        raise

    log("OK", "Element type set to 10-noded tetrahedra")

    log("INFO", "Setting mesh gradation to Uniform...")

    try:
        mesh.setMeshGradation(MeshGradation.UNIFORM)
    except Exception as error:
        log("ERROR", f"Could not set mesh gradation: {error}")
        raise

    log("OK", "Mesh gradation set to Uniform")

    log("INFO", "Generating the mesh...")
    log("WARNING", "Meshing may take a significant amount of time.")

    try:
        mesh.mesh()
    except Exception as error:
        log("ERROR", f"Mesh generation failed: {error}")
        raise

    log("OK", "Mesh generation completed")


# =============================================================================
# STEP 10: CLOSE AND REOPEN DISPLACEMENT MODEL
# =============================================================================

def close_model(model, save_changes=True):
    """Close an RS3 model safely."""

    try:
        model.close(save_changes)
    except Exception as error:
        log("WARNING", f"Could not close the model cleanly: {error}")


def reopen_displacement_model(modeler):
    """Reopen F256_DISP before computation."""

    log_step(10, "REOPEN DISPLACEMENT MODEL")

    if not Config.DISP_MODEL.exists():
        raise FileNotFoundError(
            f"Displacement model was not found: {Config.DISP_MODEL}"
        )

    log("INFO", f"Opening: {Config.DISP_MODEL.name}")

    try:
        model = modeler.openFile(str(Config.DISP_MODEL))
    except Exception as error:
        log("ERROR", f"Could not reopen the model: {error}")
        raise

    log("OK", "Displacement model reopened")
    return model


# =============================================================================
# STEP 11: COMPUTE DISPLACEMENT MODEL
# =============================================================================

def compute_displacement(model):
    """Compute the displacement and stress model."""

    log_step(11, "COMPUTE DISPLACEMENT MODEL")

    log("INFO", "Starting RS3 computation...")
    log("WARNING", "The computation may take several hours.")

    try:
        model.Compute.compute()
    except Exception as error:
        log("ERROR", f"Displacement computation failed: {error}")
        raise

    log("OK", "RS3 computation process completed")

    return check_stage_convergence(model)


def check_stage_convergence(model):
    """Read and report stage convergence."""

    log("INFO", "Reading stage convergence status...")

    try:
        success, error_message, convergence_status = (
            model.Compute.readConvergenceStatus()
        )
    except Exception as error:
        log("WARNING", f"Could not read convergence status: {error}")
        return False

    if not success:
        log("ERROR", f"Computation was not successful: {error_message}")
        return False

    log("OK", "Computation completed successfully")

    if hasattr(convergence_status, "StagesConvergence"):
        stage_results = convergence_status.StagesConvergence

        for stage_item in stage_results:
            if isinstance(stage_item, tuple) and len(stage_item) >= 2:
                stage_number = stage_item[0]
                converged = stage_item[1]

                status = "CONVERGED" if converged else "FAILED"
                log("INFO", f"Stage {stage_number}: {status}")

        all_converged = all(
            item[1]
            for item in stage_results
            if isinstance(item, tuple) and len(item) >= 2
        )

        return all_converged

    log("WARNING", "No detailed stage-convergence list was returned")
    return True


# =============================================================================
# STEP 12: MANUAL RESULT EXPORT
# =============================================================================

def manual_displacement_export_pause():
    """Pause while displacement and stress data are exported manually."""

    log_step(12, "MANUAL STEP: EXPORT DISPLACEMENT AND STRESS RESULTS")

    log("ACTION", "Open the RS3 Interpret results.")
    print()

    log("ACTION", "Export Total Displacement:")
    log("ACTION", "  1. Select Total Displacement.")
    log("ACTION", "  2. Export mesh or nodal results to CSV.")
    log(
        "ACTION",
        f"  3. Save as: "
        f"{Config.OUTPUT_PATH / 'F256_Displacement_Results.csv'}"
    )
    print()

    log("ACTION", "Export Major Principal Stress:")
    log("ACTION", "  1. Select Major Principal Stress.")
    log("ACTION", "  2. Export mesh or element results to CSV.")
    log(
        "ACTION",
        f"  3. Save as: "
        f"{Config.OUTPUT_PATH / 'F256_PrincipalStress_Results.csv'}"
    )

    pause("Press ENTER after the result files have been exported...")

    log("OK", "Manual result export acknowledged")


# =============================================================================
# STEP 13: CREATE SRF MODEL
# =============================================================================

def create_srf_model():
    """Copy the displacement file and create the SRF model."""

    log_step(13, "CREATE SRF MODEL")

    if not Config.DISP_MODEL.exists():
        raise FileNotFoundError(
            f"Displacement model was not found: {Config.DISP_MODEL}"
        )

    if Config.SRF_MODEL.exists():
        log("WARNING", f"Existing SRF model will be replaced: {Config.SRF_MODEL}")
        Config.SRF_MODEL.unlink()

    log(
        "INFO",
        f"Copying {Config.DISP_MODEL.name} to {Config.SRF_MODEL.name}..."
    )

    try:
        shutil.copy2(Config.DISP_MODEL, Config.SRF_MODEL)
    except Exception as error:
        log("ERROR", f"Could not create the SRF model: {error}")
        raise

    log("OK", f"SRF model created: {Config.SRF_MODEL}")


def open_srf_model(modeler):
    """Open the copied SRF model."""

    log_step(14, "OPEN SRF MODEL")

    log("INFO", f"Opening: {Config.SRF_MODEL.name}")

    try:
        model_srf = modeler.openFile(str(Config.SRF_MODEL))
    except Exception as error:
        log("ERROR", f"Could not open the SRF model: {error}")
        raise

    log("OK", "SRF model opened")
    return model_srf


# =============================================================================
# STEP 15: ENABLE SRF MANUALLY
# =============================================================================

def manual_srf_enable_pause():
    """Pause while SRF is enabled in the RS3 project settings."""

    log_step(15, "MANUAL STEP: ENABLE SRF ANALYSIS")

    log("ACTION", "In the open F256_SRF model:")
    log("ACTION", "  1. Open Analysis > Project Settings.")
    log("ACTION", "  2. Open the Shear Strength Reduction settings.")
    log("ACTION", "  3. Enable Determine Strength Reduction Factor.")
    log("ACTION", "  4. Initial SRF estimate = 1.0.")
    log("ACTION", "  5. Step size = Automatic.")
    log("ACTION", "  6. SRF tolerance = 0.01.")
    log("ACTION", "  7. Confirm Vx and Dio use direct Hoek-Brown reduction.")
    log("ACTION", "  8. Confirm Fill uses Mohr-Coulomb reduction.")
    log("ACTION", "  9. Click OK.")
    log("ACTION", " 10. Save the SRF model using File > Save.")

    pause("Press ENTER after SRF has been enabled and saved...")

    log("OK", "SRF configuration acknowledged")


# =============================================================================
# STEP 16: COMPUTE SRF
# =============================================================================

def compute_srf(model_srf):
    """Compute the SRF model."""

    log_step(16, "COMPUTE SRF MODEL")

    log("INFO", "Starting SRF computation...")
    log("WARNING", "The SRF computation may take several hours.")

    try:
        model_srf.Compute.compute()
    except Exception as error:
        log("ERROR", f"SRF computation failed: {error}")
        raise

    log("OK", "SRF computation process completed")

    try:
        success, error_message, convergence_status = (
            model_srf.Compute.readConvergenceStatus()
        )
    except Exception as error:
        log("WARNING", f"Could not read SRF convergence status: {error}")
        return False

    if not success:
        log("ERROR", f"SRF computation was not successful: {error_message}")
        return False

    log("OK", "SRF computation completed successfully")

    if hasattr(convergence_status, "SrfValuesConvergence"):
        srf_values = convergence_status.SrfValuesConvergence

        log("INFO", "Last SRF trial results:")

        for srf_item in srf_values[-10:]:
            if isinstance(srf_item, tuple) and len(srf_item) >= 2:
                srf_value = srf_item[0]
                converged = srf_item[1]

                status = "CONVERGED" if converged else "FAILED"
                log("INFO", f"SRF trial {srf_value:.4f}: {status}")

    return True


# =============================================================================
# STEP 17: EXPORT SRF CONVERGENCE HISTORY
# =============================================================================

def export_srf_convergence_history(model_srf):
    """
    Export the SRF trial convergence history.

    This function does not claim that the highest converged trial equals the
    finalRS3 Factor of Safety. The final FoS must be confirmed in RS3.
    """

    log_step(17, "EXPORT SRF CONVERGENCE HISTORY")

    try:
        success, error_message, convergence_status = (
            model_srf.Compute.readConvergenceStatus()
        )
    except Exception as error:
        log("WARNING", f"Could not read SRF convergence data: {error}")
        return

    if not success:
        log("WARNING", f"Could not retrieve SRF history: {error_message}")
        return

    if not hasattr(convergence_status, "SrfValuesConvergence"):
        log("WARNING", "No SRF trial-convergence history was returned")
        return

    srf_values = convergence_status.SrfValuesConvergence

    try:
        with open(Config.SRF_SUMMARY, "w", encoding="utf-8") as output_file:
            output_file.write("F#256 SRF TRIAL CONVERGENCE HISTORY\n")
            output_file.write("=" * 60 + "\n\n")

            for srf_item in srf_values:
                if isinstance(srf_item, tuple) and len(srf_item) >= 2:
                    srf_value = srf_item[0]
                    converged = srf_item[1]

                    status = "CONVERGED" if converged else "FAILED"
                    output_file.write(
                        f"SRF trial {srf_value:.4f}: {status}\n"
                    )

            output_file.write("\n")
            output_file.write(
                "IMPORTANT: This file contains the SRF trial-convergence "
                "history only.\n"
            )
            output_file.write(
                "Confirm the final reported Factor of Safety in the "
                "RS3 SRF results interface.\n"
            )

    except Exception as error:
        log("WARNING", f"Could not write the SRF history file: {error}")
        return

    log("OK", f"SRF history exported: {Config.SRF_SUMMARY}")
    log(
        "ACTION",
        "Open the RS3 SRF results and record the final reported Factor of Safety."
    )


# =============================================================================
# MAIN WORKFLOW
# =============================================================================

def main():
    """Run the complete F#256 RS3 workflow."""

    print()
    print("=" * 80)
    print("F#256 OPEN PIT SLOPE")
    print("RS3 4.043 ROCSCRIPT AUTOMATION")
    print("=" * 80)
    print()

    model = None
    model_srf = None

    try:
        # 1. Validate files
        validate_inputs()

        # 2. Connect to RS3
        modeler = connect_to_rs3()

        # 3. Open the prepared template
        model = open_template(modeler)

        # 4. Import DXF topography
        import_dxf_surface(model)

        # 5. Protect the template by saving immediately as F256_DISP
        save_displacement_model(model)

        # 6. Verify that the surface trims the external volume
        manual_surface_check_pause()

        # 7. Import block model and verify material mapping
        manual_block_model_import_pause()

        # 8. Set the global mesh size manually
        manual_mesh_size_pause()

        # 9. Generate the mesh through RocScript
        generate_mesh(model)

        # Save and close before reopening for computation
        close_model(model, save_changes=True)
        model = None

        # 10. Reopen F256_DISP
        model = reopen_displacement_model(modeler)

        # 11. Compute stress and displacement model
        displacement_converged = compute_displacement(model)

        if not displacement_converged:
            raise RuntimeError(
                "The displacement analysis did not converge. "
                "SRF analysis will not be started."
            )

        # 12. Export displacement and stress manually
        manual_displacement_export_pause()

        # Close before copying the file
        close_model(model, save_changes=True)
        model = None

        # 13. Create SRF model
        create_srf_model()

        # 14. Open SRF model
        model_srf = open_srf_model(modeler)

        # 15. Enable SRF analysis manually
        manual_srf_enable_pause()

        # 16. Compute SRF model
        srf_success = compute_srf(model_srf)

        if not srf_success:
            raise RuntimeError(
                "The SRF analysis did not complete successfully."
            )

        # 17. Export trial convergence history
        export_srf_convergence_history(model_srf)

        close_model(model_srf, save_changes=True)
        model_srf = None

        print()
        print("=" * 80)
        log("OK", "F#256 AUTOMATION WORKFLOW COMPLETED")
        print("=" * 80)
        print()

        log("INFO", f"Displacement model: {Config.DISP_MODEL}")
        log("INFO", f"SRF model: {Config.SRF_MODEL}")
        log("INFO", f"SRF history: {Config.SRF_SUMMARY}")
        log(
            "ACTION",
            "Confirm the final Factor of Safety in the RS3 SRF results."
        )

    except KeyboardInterrupt:
        print()
        log("WARNING", "The workflow was stopped by the user.")

        if model is not None:
            close_model(model, save_changes=True)

        if model_srf is not None:
            close_model(model_srf, save_changes=True)

        sys.exit(1)

    except Exception as error:
        print()
        print("=" * 80)
        log("FATAL", str(error))
        print("=" * 80)

        if model is not None:
            close_model(model, save_changes=True)

        if model_srf is not None:
            close_model(model_srf, save_changes=True)

        sys.exit(1)


if __name__ == "__main__":
    main()
