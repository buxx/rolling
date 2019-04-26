pub mod zone;

extern crate num_cpus;
use crate::map::generator::zone::ZoneGenerator;
use crate::map::world::World;
use crate::tile::world::types as world_types;
use crate::tile::world::types::WorldTile;
use crate::tile::zone::types as zone_types;
use crate::RollingError;
use crossbeam::channel::unbounded;
use rayon::prelude::*;
use std::mem;
use std::path::Path;
use std::sync::{Arc, Mutex};

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

        let mut progress = Arc::new(Mutex::new(create_empty_progress(self.world)));
        let cpu_count: usize = num_cpus::get();
        println!("cpus: {}", cpu_count);
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(cpu_count)
            .build()
            .unwrap();
        let mut tile_positions: Vec<(usize, usize, &WorldTile)> = Vec::new();
        let current_job_pool_start = Arc::new(Mutex::new(0));
        for (row_i, row) in self.world.rows.iter().enumerate() {
            for (col_i, world_tile) in row.iter().enumerate() {
                tile_positions.push((row_i, col_i, &world_tile));
            }
        }
        let job_count = tile_positions.len();

        pool.install(|| {
            let current_job_pool_start = Arc::clone(&current_job_pool_start);
            (0..job_count / cpu_count).into_par_iter().for_each(|_i| {
                let (sender, receiver) = unbounded();
                let mut current_job_pool_start_ = current_job_pool_start.lock().unwrap();

                (0..cpu_count).into_par_iter().for_each(|j| {
                    let thread_sender = sender.clone();

                    let current_job_index = *current_job_pool_start_ + j;
                    let (row_i, col_i, world_tile) = tile_positions[current_job_index];
                    let target_path =
                        Path::new(target_folder).join(format!("{}-{}.txt", row_i, col_i));
                    let zone_generator = self.get_zone_generator(&world_tile);

                    match zone_generator.generate(target_path.as_path(), width, height) {
                        Err(_) => {
                            // FIXME
                            //                            return Err(RollingError::new(format!(
                            //                                "Error during generation of {}-{}.txt: {}",
                            //                                row_i, col_i, e
                            //                            )));
                        }
                        Ok(_) => {
                            thread_sender.send((row_i, col_i)).unwrap();
                        }
                    }
                });
                drop(sender);

                for (done_row_i, done_col_i) in receiver {
                    let progress_ = Arc::clone(&progress);
                    let mut current_progress = progress_.lock().unwrap();
                    let new_progress = create_updated_progress(
                        &current_progress,
                        done_row_i,
                        done_col_i,
                        self.world,
                    );
                    //                    current_progress = String::from(new_progress);
                    *current_progress = new_progress;
                    println!("{}", current_progress);
                }
                *current_job_pool_start_ += cpu_count;
                //  FIXME : release ? seems blocked some times
                println!()
            });
        });

        //        thread::scope(|scope| {
        //            for (row_i, row) in self.world.rows.iter().enumerate() {
        //                for (col_i, world_tile) in row.iter().enumerate() {
        //                    let thread_s = sender.clone();
        //                    scope.spawn(move |_| {
        //                        // TODO BS 2019-04-09: These char are visible only when line is end
        //                        print!("{}", self.world.geo_chars[row_i][col_i]);
        //                        let target_path =
        //                            Path::new(target_folder).join(format!("{}-{}.txt", row_i, col_i));
        //                        let zone_generator = self.get_zone_generator(&world_tile);
        //
        //                        match zone_generator.generate(target_path.as_path(), width, height) {
        //                            Err(e) => {
        //                                return Err(RollingError::new(format!(
        //                                    "Error during generation of {}-{}.txt: {}",
        //                                    row_i, col_i, e
        //                                )));
        //                            }
        //                            Ok(_) => {
        //                                thread_s.send((row_i, col_i)).unwrap();
        //                                Ok(())
        //                            }
        //                        }
        //                    });
        //                }
        //                println!();
        //            }
        //            drop(sender);
        //
        //            for (done_row_i, done_col_i) in receiver {
        //                progress = create_updated_progress(&progress, done_row_i, done_col_i, self.world);
        //                println!("{}", progress);
        //            }
        //        })
        //        .unwrap();

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
