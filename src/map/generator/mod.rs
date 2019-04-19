pub mod zone;

use crate::map::generator::zone::ZoneGenerator;
use crate::map::world::World;
use crate::tile::world::types as world_types;
use crate::tile::zone::types as zone_types;
use crate::RollingError;
use crossbeam::channel::unbounded;
use crossbeam::thread;
use std::path::Path;

pub struct Generator<'a> {
    world: &'a World<'a>,
}

impl<'a> Generator<'a> {
    pub fn new(world: &'a World) -> Generator<'a> {
        Generator { world: &world }
    }
}

fn create_empty_progress(world: &World) -> String {
    let mut progress: String = String::new();
    for row in world.rows.iter() {
        for _ in row.iter() {
            progress.push_str(" ");
        }
        progress.push_str("\n");
    }
    progress
}

fn create_updated_progress(
    progress: &String,
    done_row_i: usize,
    done_col_i: usize,
    world: &World,
) -> String {
    let mut progress_vec: Vec<&str> = progress.split("\n").collect();
    let change_row = progress_vec[done_row_i];
    let mut new_row = String::new();
    for (current_str_i, current_str) in change_row.chars().enumerate() {
        if current_str_i == done_col_i {
            new_row.push_str(&world.geo_chars[done_row_i][done_col_i].to_string());
        } else {
            new_row.push_str(&current_str.to_string());
        }
    }
    progress_vec[done_row_i] = new_row.as_str();
    progress_vec.join("\n")
}

impl<'a> Generator<'a> {
    pub fn generate(
        &self,
        target_folder: &Path,
        width: u32,
        height: u32,
    ) -> Result<(), RollingError> {
        println!(
            "target is {} for {} and {}",
            target_folder.display(),
            width,
            height
        );

        // Prepare progress string
        let mut progress = create_empty_progress(self.world);

        println!("{}", progress);
        let (sender, receiver) = unbounded();

        thread::scope(|scope| {
            for (row_i, row) in self.world.rows.iter().enumerate() {
                for (col_i, world_tile) in row.iter().enumerate() {
                    let thread_s = sender.clone();
                    scope.spawn(move |_| {
                        // TODO BS 2019-04-09: These char are visible only when line is end
                        print!("{}", self.world.geo_chars[row_i][col_i]);
                        let target_path =
                            Path::new(target_folder).join(format!("{}-{}.txt", row_i, col_i));
                        let zone_generator = self.get_zone_generator(&world_tile);

                        match zone_generator.generate(target_path.as_path(), width, height) {
                            Err(e) => {
                                return Err(RollingError::new(format!(
                                    "Error during generation of {}-{}.txt: {}",
                                    row_i, col_i, e
                                )));
                            }
                            Ok(_) => {
                                thread_s.send((row_i, col_i)).unwrap();
                                Ok(())
                            }
                        }
                    });
                }
                println!();
            }
            drop(sender);

            for (done_row_i, done_col_i) in receiver {
                progress = create_updated_progress(&progress, done_row_i, done_col_i, self.world);
                println!("{}", progress);
            }
        })
        .unwrap();

        Ok(())
    }

    fn get_zone_generator(&self, world_tile: &world_types::WorldTile) -> impl zone::ZoneGenerator {
        match world_tile {
            world_types::WorldTile::Beach => zone::DefaultGenerator {
                world: self.world,
                default_tile: &zone_types::ZoneTile::Sand,
            },
            world_types::WorldTile::Sea => zone::DefaultGenerator {
                world: self.world,
                default_tile: &zone_types::ZoneTile::SaltedWater,
            },
            world_types::WorldTile::Mountain => zone::DefaultGenerator {
                world: self.world,
                default_tile: &zone_types::ZoneTile::RockyGround,
            },
            world_types::WorldTile::Plain => zone::DefaultGenerator {
                world: self.world,
                default_tile: &zone_types::ZoneTile::ShortGrass,
            },
        }
    }
}
