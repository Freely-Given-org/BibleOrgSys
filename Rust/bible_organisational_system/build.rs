use std::process::Command;

fn main() {
    let crate_root = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let workspace_root = std::path::Path::new(&crate_root)
        .parent()
        .and_then(|p| p.parent())
        .expect("could not find workspace root");
    let output_dir = workspace_root.join("typings");

    // Re-run when source changes
    println!("cargo::rerun-if-changed=src");

    let status = Command::new("uvx")
        .args(["rylai", &crate_root, "-o"])
        .arg(&output_dir)
        .status();

    match status {
        Ok(s) if s.success() => {}
        Ok(s) => eprintln!("cargo:warning=rylai exited with {s}, stubs may be outdated"),
        Err(e) => eprintln!("cargo:warning=could not run rylai: {e}, stubs may be outdated"),
    }
}
