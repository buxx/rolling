use crate::RollingError;
use std::error::Error;
use std::fs;
use std::io::Read;
use std::path::Path;

pub const BLOCK_GEO: &str = "GEO";
pub const BLOCK_LEGEND: &str = "LEGEND";

pub fn extract_block_from_source(
    block_name: &str,
    source: &String,
) -> Result<String, RollingError> {
    let mut block_found = false;
    let mut block_lines: Vec<&str> = Vec::new();

    for line in source.lines() {
        if line.starts_with("::") {
            // TODO BS 2019-04-03: there is strip method ?
            let line_block_name = line.replace("::", "").replace("\n", "").replace(" ", "");
            if line_block_name == block_name {
                block_found = true;
            } else if block_found {
                return Ok(block_lines.join("\n"));
            }
        } else if block_found {
            block_lines.push(line);
        }
    }

    if block_found {
        return Ok(block_lines.join("\n"));
    }
    Err(RollingError::new(format!(
        "Block \"{}\" not found",
        block_name
    )))
}

pub fn get_file_content(file_path: &Path) -> Result<String, Box<Error>> {
    let mut file = fs::File::open(file_path)?;
    let mut file_content = String::new();
    file.read_to_string(&mut file_content)?;
    Ok(file_content)
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn extract_block_from_source_ok_one_block() {
        let result =
            extract_block_from_source("BLOCK_NAME", &String::from("::BLOCK_NAME\nline1\nline2"));
        assert_eq!(String::from("line1\nline2"), result.unwrap())
    }

    #[test]
    fn extract_block_from_source_ok_second_block() {
        let result = extract_block_from_source(
            "BLOCK_NAME",
            &String::from("::BLOCKA\nlinea\n::BLOCK_NAME\nline1\nline2"),
        );
        assert_eq!(String::from("line1\nline2"), result.unwrap())
    }

    #[test]
    fn extract_block_from_source_ok_not_last_block() {
        let result = extract_block_from_source(
            "BLOCKA",
            &String::from("::BLOCKA\nlinea\n::BLOCK_NAME\nline1\nline2"),
        );
        assert_eq!(String::from("linea"), result.unwrap())
    }

    #[test]
    #[should_panic]
    fn extract_block_from_source_err_no_block() {
        extract_block_from_source(
            "BLOCK_NAME_UNKNOWN",
            &String::from("::BLOCK_NAME\nline1\nline2"),
        )
        .unwrap();
    }
}
