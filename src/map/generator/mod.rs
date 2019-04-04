pub mod zone;

use std::path::Path;
use crate::map::world::World;
use crate::tile::world::types as world_types;
use crate::tile::zone::types as zone_types;
use crate::map::generator::zone::ZoneGenerator;
use crate::RollingError;

pub struct Generator<'a> {
  world: &'a World<'a>,
}

impl<'a> Generator<'a> {
  pub fn new(world: &'a World) -> Generator<'a> {
    Generator {
      world: &world,
    }
  }
}

impl<'a> Generator<'a> {
  pub fn generate(&self, target_folder: &Path, width: u32, height: u32) -> Result<(), RollingError> {
    println!("target is {} for {} and {}", target_folder.display(), width, height);
    for (row_i, row) in self.world.rows.iter().enumerate() {
      for (col_i, world_tile) in row.iter().enumerate() {
        // TODO BS 2019-04-09: These char are visible only when line is end
        print!("{}", self.world.geo_chars[row_i][col_i]);
        let target_path = Path::new(target_folder).join(format!("{}-{}.txt", row_i, col_i));
        let zone_generator = self.get_zone_generator(&world_tile);

        match zone_generator.generate(target_path.as_path(), width, height) {
          Err(e) => {return Err(RollingError::new(format!("Error during generation of {}-{}.txt: {}", row_i, col_i, e)))},
          Ok(_) => {},
        }

      }
      println!();
    }

    Ok(())
  }

  fn get_zone_generator(&self, world_tile: &world_types::WorldTile) -> impl zone::ZoneGenerator {
    match world_tile {
      world_types::WorldTile::Beach => { zone::DefaultGenerator { world: self.world, default_tile: &zone_types::ZoneTile::Sand } }
      world_types::WorldTile::Sea => { zone::DefaultGenerator { world: self.world, default_tile: &zone_types::ZoneTile::SaltedWater } }
      world_types::WorldTile::Mountain => { zone::DefaultGenerator { world: self.world, default_tile: &zone_types::ZoneTile::RockyGround } }
      world_types::WorldTile::Plain => { zone::DefaultGenerator { world: self.world, default_tile: &zone_types::ZoneTile::ShortGrass } }
    }
  }
}
