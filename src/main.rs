use std::path::Path;
use std::process::exit;
use std::fs;

pub mod tile;
pub mod map;
pub mod util;


#[derive(Debug)]
pub struct RollingError {
  pub message: String,
}

impl RollingError {
  pub fn new(message: String) -> RollingError {
    RollingError{message}
  }
}


// Question: can we declare variable in mod ?
fn main() {
  // TODO BS 2019-04-07: from cli args
  let source = match util::get_file_content("tests/src/worldmapb.txt") {
    Ok(file_content) => {file_content},
    Err(e) => {panic!("Unable to retrieve world map content: {}", e)},
  };

  let legend = match tile::world::legend::WorldMapLegend::new(&source) {
    Ok(legend) => {legend},
    Err(e) => {println!("{}", e.message); exit(1)}
  };
  let world = match map::world::World::new(&source, &legend) {
    Ok(world) => {world},
    Err(e) => {println!("{}", e.message); exit(1)}
  };
  let zone_generator = map::generator::Generator::new(&world);
  // TODO BS 2019-04-07 from cli arg
  fs::create_dir_all("./map_test").unwrap();
  let target_path = Path::new("./map_test");

  match zone_generator.generate(&target_path, 33, 33) {
    Err(e) => {println!("{}", e.message); exit(1)},
    Ok(_) => {},
  }

  println!("foo: {}", tile::zone::types::get_char_for_tile(&tile::zone::types::ZoneTile::DryBush));
}
