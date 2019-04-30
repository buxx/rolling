use super::super::world;
use crate::tile::zone::types;
use std::error::Error;
use std::fs::File;
use std::io::Write;
use std::path::Path;

pub trait ZoneGenerator<'a> {
    fn generate(&self, target: &'a Path, width: u32, height: u32) -> Result<(), Box<Error>>;
}

pub struct DefaultGenerator<'a> {
    pub world: &'a world::World<'a>,
    pub default_tile: &'a types::ZoneTile,
}

fn is_out_zone(width: i32, height: i32, tested_row_i: i32, tested_col_i: i32) -> bool {
    let row_part_len = (width - 1) / 4;
    let col_part_len = (height - 1) / 4;

    // exclude middle
    if tested_row_i > col_part_len && tested_row_i < height - col_part_len {
        return false;
    }

    // case of top
    if tested_row_i < height / 2 {
        let end_left = row_part_len - tested_row_i;
        let start_right = width - row_part_len + tested_row_i;

        if tested_col_i < end_left {
            return true;
        }
        if tested_col_i >= start_right {
            return true;
        }
    // case of bottom
    } else {
        let end_left = row_part_len - (height - (tested_row_i + 1));
        let start_right = width - row_part_len + height - (tested_row_i + 1);

        if tested_col_i < end_left {
            return true;
        }
        if tested_col_i >= start_right {
            return true;
        }
    }

    false
}

impl<'a> ZoneGenerator<'a> for DefaultGenerator<'a> {
    fn generate(&self, target: &'a Path, width: u32, height: u32) -> Result<(), Box<Error>> {
        let mut final_string = String::new();
        for row_i in 0..height {
            let mut row_string = String::new();
            for col_i in 0..width {
                if is_out_zone(width as i32, height as i32, row_i as i32, col_i as i32) {
                    row_string.push(' ');
                } else {
                    let tile_char = types::get_char_for_tile(self.default_tile);
                    row_string.push(tile_char);
                }
            }
            row_string.push_str("\n");
            final_string.extend(row_string.chars());
        }

        let mut zone_file = File::create(&target)?;
        zone_file.write_all(final_string.as_bytes())?;

        Ok(())
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn is_outzone_ok() {
        // First line
        assert_eq!(true, is_out_zone(13, 13, 0, 0));
        assert_eq!(true, is_out_zone(13, 13, 0, 1));
        assert_eq!(true, is_out_zone(13, 13, 0, 2));
        assert_eq!(false, is_out_zone(13, 13, 0, 3));
        assert_eq!(false, is_out_zone(13, 13, 0, 9));
        assert_eq!(true, is_out_zone(13, 13, 0, 10));
        assert_eq!(true, is_out_zone(13, 13, 0, 11));
        assert_eq!(true, is_out_zone(13, 13, 0, 12));

        // second line
        assert_eq!(true, is_out_zone(13, 13, 1, 0));
        assert_eq!(true, is_out_zone(13, 13, 1, 1));
        assert_eq!(false, is_out_zone(13, 13, 1, 2));
        assert_eq!(false, is_out_zone(13, 13, 1, 10));
        assert_eq!(true, is_out_zone(13, 13, 1, 11));
        assert_eq!(true, is_out_zone(13, 13, 1, 12));

        // Last line
        assert_eq!(true, is_out_zone(13, 13, 12, 0));
        assert_eq!(true, is_out_zone(13, 13, 12, 1));
        assert_eq!(true, is_out_zone(13, 13, 12, 2));
        assert_eq!(false, is_out_zone(13, 13, 12, 3));
        assert_eq!(false, is_out_zone(13, 13, 12, 9));
        assert_eq!(true, is_out_zone(13, 13, 12, 10));
        assert_eq!(true, is_out_zone(13, 13, 12, 11));
        assert_eq!(true, is_out_zone(13, 13, 12, 12));

        // before last line
        assert_eq!(true, is_out_zone(13, 13, 11, 0));
        assert_eq!(true, is_out_zone(13, 13, 11, 1));
        assert_eq!(false, is_out_zone(13, 13, 11, 2));
        assert_eq!(false, is_out_zone(13, 13, 11, 10));
        assert_eq!(true, is_out_zone(13, 13, 11, 11));
        assert_eq!(true, is_out_zone(13, 13, 11, 12));
    }
}
