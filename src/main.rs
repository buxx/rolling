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

    let source = util::get_file_content(&opt.world_map_file_path).unwrap_or_else(|e| {
        eprintln!("Unable to retrieve world map content: {}", e);
        exit(1);
    });

    let legend = tile::world::legend::WorldMapLegend::new(&source).unwrap_or_else(|e| {
        eprintln!("{}", e.message);
        exit(1)
    });
    let world = map::world::World::new(&source, &legend).unwrap_or_else(|e| {
        eprintln!("{}", e.message);
        exit(1);
    });
    let zone_generator = map::generator::Generator::new(&world);

    fs::create_dir_all(&opt.output).unwrap();
    let target_path = Path::new(&opt.output);

    zone_generator
        .generate(&target_path, opt.width, opt.height)
        .unwrap_or_else(|e| {
            eprintln!("{}", e.message);
            exit(1);
        });

    println!(
        "foo: {}",
        tile::zone::types::get_char_for_tile(&tile::zone::types::ZoneTile::DryBush)
    );
}
