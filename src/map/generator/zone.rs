use super::super::world;
use std::path::Path;
use crate::tile::zone::types;
use std::fs::File;
use std::io;
use std::io::Write;

pub trait ZoneGenerator<'a> {
  fn generate(&self, target: &'a Path, width: u32, height: u32) -> Result<(), io::Error>;
}


pub struct DefaultGenerator<'a> {
  pub world: &'a world::World<'a>,
  pub default_tile: &'a types::ZoneTile,
}

impl<'a> ZoneGenerator<'a> for DefaultGenerator<'a> {
  fn generate(&self, target: &'a Path, width: u32, height: u32) -> Result<(), io::Error> {
    let mut final_string = String::new();
    for _row_i in 0..height {
      let mut row_string = String::new();
      for _col_i in 0..width {
        let tile_char = types::get_char_for_tile(self.default_tile);
        row_string.push(tile_char);
      }
      row_string.push_str("\n");
      final_string.extend(row_string.chars());
    }

    let mut zone_file = File::create(&target)?;
    zone_file.write_all(final_string.as_bytes())?;

    Ok(())
  }
}
