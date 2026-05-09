use std::process::Command;

fn main() {
    println!("cargo::rerun-if-changed=build_static_tables.py");
    println!("cargo::rerun-if-changed=lib.src.rs");
    println!("cargo::rerun-if-changed=USFM3Markers_Tables.tsv");

    let output = Command::new("python3")
        .arg("build_static_tables.py")
        .output()
        .expect("Failed to execute python build script");

    if !output.status.success() {
        panic!("Python build script failed: {}", String::from_utf8_loss_of_any(output.stderr));
    }
}

// Helper trait to allow String conversion from potentially invalid utf8 (for errors)
trait LossyUtf8 {
    fn from_utf8_loss_of_any(bytes: Vec<u8>) -> String;
}

impl LossyUtf8 for String {
    fn from_utf8_loss_of_any(bytes: Vec<u8>) -> String {
        String::from_utf8_lossy(&bytes).into_owned()
    }
}
