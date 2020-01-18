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

pub fn get_file_content(file_path: &Path) -> Result<String, Box<dyn Error>> {
    let mut file = fs::File::open(file_path)?;
    let mut file_content = String::new();
    file.read_to_string(&mut file_content)?;
    Ok(file_content)
}

pub fn last_char_is(searched_char: char, chars: &Vec<Vec<char>>) -> bool {
    if chars.is_empty() || chars.last().unwrap().is_empty() {
        return false;
    }

    let last_line: &Vec<char> = chars.last().unwrap();
    let inverted_last_line: Vec<&char> = last_line.iter().rev().collect();

    return inverted_last_line[0] == &searched_char;
}

pub fn top_chars_contains(searched_char: char, chars: &Vec<Vec<char>>) -> bool {
    // Consider chars lines length minimum of 3 chars

    if chars.len() < 2 {
        return false;
    }

    let inverted_lines: Vec<&Vec<char>> = chars.iter().rev().collect();
    let previous_line_len = inverted_lines[1].len();
    let ref_char_position = inverted_lines[0].len();

    let mut test_positions: Vec<usize> = Vec::new();

    if ref_char_position == 0 {
        test_positions.push(0);
        test_positions.push(1);
    } else if ref_char_position == previous_line_len - 1 {
        test_positions.push(ref_char_position - 1);
        test_positions.push(ref_char_position);
    } else if ref_char_position == previous_line_len {
        test_positions.push(ref_char_position - 1);
    } else {
        test_positions.push(ref_char_position - 1);
        test_positions.push(ref_char_position);
        test_positions.push(ref_char_position + 1);
    }

    for test_position in test_positions.into_iter() {
        if inverted_lines[1][test_position] == searched_char {
            return true;
        }
    }

    false
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

    #[test]
    fn last_char_is_ok() {
        let chars = vec![vec![]];
        assert!(!last_char_is('a', &chars));

        let chars = vec![vec!['a']];
        assert!(last_char_is('a', &chars));

        let chars = vec![vec!['a', 'b']];
        assert!(!last_char_is('a', &chars));

        let chars = vec![vec!['a', 'b', 'c']];
        assert!(!last_char_is('a', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec![]];
        assert!(!last_char_is('a', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec!['a']];
        assert!(last_char_is('a', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec!['a', 'b']];
        assert!(!last_char_is('a', &chars));
    }

    #[test]
    fn top_chars_contains_ok() {
        let chars = vec![vec![]];
        assert!(!top_chars_contains('a', &chars));

        let chars = vec![vec!['a', 'b', 'c']];
        assert!(!top_chars_contains('a', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec![]];
        assert!(top_chars_contains('a', &chars));
        assert!(top_chars_contains('b', &chars));
        assert!(!top_chars_contains('c', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec!['x']];
        assert!(top_chars_contains('a', &chars));
        assert!(top_chars_contains('b', &chars));
        assert!(top_chars_contains('c', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec!['x', 'y']];
        assert!(!top_chars_contains('a', &chars));
        assert!(top_chars_contains('b', &chars));
        assert!(top_chars_contains('c', &chars));

        let chars = vec![vec!['a', 'b', 'c'], vec!['x', 'y', 'z']];
        assert!(!top_chars_contains('a', &chars));
        assert!(!top_chars_contains('b', &chars));
        assert!(top_chars_contains('c', &chars));
    }
}
