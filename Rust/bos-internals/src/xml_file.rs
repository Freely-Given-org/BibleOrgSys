//! XML file loading and validation logic.

use std::path::Path;
use quick_xml::Reader;
use quick_xml::events::Event;
use std::process::Command;

/// Results of XML validation.
pub struct XmlValidationResults {
    pub validated_by_loading: bool,
    pub validated_with_lint: Option<bool>,
    pub error_string: Option<String>,
    pub stdout: Option<String>,
    pub stderr: Option<String>,
}

/// Check if an XML file is well-formed using quick-xml.
pub fn validate_well_formedness<P: AsRef<Path>>(path: P) -> Result<(), String> {
    let mut reader = match Reader::from_file(&path) {
        Ok(r) => r,
        Err(e) => return Err(format!("Unable to open file: {}", e)),
    };
    let mut buf = Vec::new();
    loop {
        match reader.read_event_into(&mut buf) {
            Ok(Event::Eof) => break,
            Ok(_) => (),
            Err(e) => return Err(format!("XML Parse Error at position {}: {}", reader.buffer_position(), e)),
        }
        buf.clear();
    }
    Ok(())
}

/// Validate XML using external xmllint.
pub fn validate_with_xmllint<P: AsRef<Path>>(
    xml_path: P,
    schema_path: Option<&str>,
) -> (Option<bool>, Option<String>, Option<String>, Option<i32>) {
    let mut cmd = Command::new("xmllint");
    cmd.arg("--noout");
    
    if let Some(schema) = schema_path {
        if schema.contains(".rng") {
            cmd.arg("--relaxng").arg(schema);
        } else {
            cmd.arg("--schema").arg(schema);
        }
    }
    
    cmd.arg(xml_path.as_ref());

    match cmd.output() {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            let success = output.status.success();
            (Some(success), Some(stdout), Some(stderr), output.status.code())
        }
        Err(e) => (None, None, Some(format!("Failed to execute xmllint: {}", e)), None),
    }
}
