use super::super::world;
use crate::tile::zone::types;
use crate::util;
use rand::distributions::WeightedIndex;
use rand::prelude::*;
use std::error::Error;
use std::fs::File;
use std::io::Write;
use std::path::Path;

pub trait ZoneGenerator<'a> {
    fn generate(&self, target: &'a Path, width: u32, height: u32) -> Result<(), Box<Error>>;
}

pub struct RandomNear<'a> {
    pub near: &'a types::ZoneTile,
    pub tile: &'a types::ZoneTile,
    pub probability: u32,
}

pub struct DefaultGenerator<'a> {
    pub world: &'a world::World<'a>,
    pub default_tile: &'a types::ZoneTile,
    pub random: Option<Vec<(f64, &'a types::ZoneTile)>>,
    pub random_near: Option<Vec<RandomNear<'a>>>,
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

fn is_there_around(searched_char: char, chars: &Vec<Vec<char>>) -> bool {
    if util::last_char_is(searched_char, chars) || util::top_chars_contains(searched_char, chars) {
        return true;
    }

    false
}

impl<'a> ZoneGenerator<'a> for DefaultGenerator<'a> {
    fn generate(&self, target: &'a Path, width: u32, height: u32) -> Result<(), Box<Error>> {
        let mut chars: Vec<Vec<char>> = Vec::new();
        let mut weights = vec![100.0];
        let mut choices = vec![self.default_tile];
        let mut rng = thread_rng();

        if self.random.is_some() {
            for random_ in self.random.as_ref().unwrap().into_iter() {
                let (random_weight, random_tile) = random_;
                weights.push(*random_weight);
                choices.push(random_tile);
            }
        }

        let distributions = WeightedIndex::new(&weights).unwrap();

        for row_i in 0..height {
            let row_chars: Vec<char> = Vec::new();
            chars.push(row_chars);

            for col_i in 0..width {
                if is_out_zone(width as i32, height as i32, row_i as i32, col_i as i32) {
                    chars.last_mut().unwrap().push(' ');
                } else {
                    let mut push_with_random = true;

                    if self.random_near.is_some() {
                        for random_near in self.random_near.as_ref().unwrap().into_iter() {
                            let searched_char = types::get_char_for_tile(random_near.near);
                            if is_there_around(searched_char, &chars) {
                                let random: f64 = rng.gen();
                                let probability: f64 = random_near.probability as f64 / 100.0;
                                if random <= probability {
                                    let tile_char = types::get_char_for_tile(random_near.tile);
                                    chars.last_mut().unwrap().push(tile_char);
                                    push_with_random = false;
                                    break;
                                }
                            }
                        }
                    }

                    if push_with_random {
                        let tile = choices[distributions.sample(&mut rng)];
                        let tile_char = types::get_char_for_tile(tile);
                        chars.last_mut().unwrap().push(tile_char);
                    }
                }
            }
        }

        let mut row_strings: Vec<String> = Vec::new();
        for row_chars in chars.iter() {
            let row_string: String = row_chars.into_iter().collect();
            row_strings.push(row_string);
        }
        let final_string = row_strings.join("\n");

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
