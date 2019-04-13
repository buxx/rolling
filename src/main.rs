extern crate structopt;

use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::process::exit;
use structopt::StructOpt;

pub mod map;
pub mod tile;
pub mod util;

#[derive(Debug)]
pub struct RollingError {
    pub message: String,
}

impl RollingError {
    pub fn new(message: String) -> RollingError {
        RollingError { message }
    }
}

#[derive(StructOpt, Debug)]
#[structopt(name = "basic")]
struct Opt {
    #[structopt(name = "WORLD_MAP_FILE", parse(from_os_str))]
    world_map_file_path: PathBuf,

    #[structopt(
        short = "o",
        long = "output-dir",
        parse(from_os_str),
        default_value = "./zones"
    )]
    output: PathBuf,

    #[structopt(short = "w", long = "width", default_value = "255")]
    width: u32,

    #[structopt(short = "h", long = "height", default_value = "255")]
    height: u32,
}

// Question: can we declare variable in mod ?
fn main() {
    let opt = Opt::from_args();

    // TODO BS 2019-04-07: from cli args
    let source = match util::get_file_content(&opt.world_map_file_path) {
        Ok(file_content) => file_content,
        Err(e) => panic!("Unable to retrieve world map content: {}", e),
    };

    let legend = match tile::world::legend::WorldMapLegend::new(&source) {
        Ok(legend) => legend,
        Err(e) => {
            println!("{}", e.message);
            exit(1)
        }
    };
    let world = match map::world::World::new(&source, &legend) {
        Ok(world) => world,
        Err(e) => {
            println!("{}", e.message);
            exit(1)
        }
    };
    let zone_generator = map::generator::Generator::new(&world);

    fs::create_dir_all(&opt.output).unwrap();
    let target_path = Path::new(&opt.output);

    match zone_generator.generate(&target_path, opt.width, opt.height) {
        Err(e) => {
            println!("{}", e.message);
            exit(1)
        }
        Ok(_) => {}
    }

    println!(
        "foo: {}",
        tile::zone::types::get_char_for_tile(&tile::zone::types::ZoneTile::DryBush)
    );
}
