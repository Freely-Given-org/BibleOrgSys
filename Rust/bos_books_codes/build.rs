use std::process::Command;

// Script to build the src/lib.rs file.
fn main() {
    // Tell Cargo that if the given file changes, to rerun this build script.
    // NOTE: none of these println outputs usually appear in the displayed build outputs.
    //  Change println! to panic! if you really want to see if it's running
    println!("cargo::rerun-if-changed=build_static_tables.py");
    println!("cargo::rerun-if-changed=lib.src.rs");
    println!("cargo::rerun-if-changed=BibleBooksCodes_Tables.tsv");

    // Run the python command to build the file src/include.rs
    let output = Command::new("python3")
        .arg("build_static_tables.py")
        .output();
        // .expect("Failed to execute command"); 

        println!("{:?}", output);
    // assert_eq!(b"SUCCESSFUL!\n", output.unwrap().stdout.as_slice());
    if !output.unwrap().stdout.contains( &36 ) { // $ Ensure we find out if the Python script failed
        panic!("Python build script failed!!!")
    }
}
