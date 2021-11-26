use super::super::world;
use crate::map::world::World;
use crate::tile::world::types as world_types;
use crate::tile::zone::types;
use crate::util;
use rand::distributions::WeightedIndex;
use rand::prelude::*;
use std::error::Error;
use std::fs::File;
use std::io::Write;
use std::path::Path;

#[derive(PartialEq, Debug)]
pub enum Border {
    TopLeft(u32),
    Top(u32),
    TopRight(u32),
    Right(u32),
    BottomRight(u32),
    Bottom(u32),
    BottomLeft(u32),
    Left(u32),
}

pub trait ZoneGenerator<'a> {
    fn generate(
        &self,
        target: &'a Path,
        width: u32,
        height: u32,
        zone_row_i: u32,
        zone_col_i: u32,
    ) -> Result<(), Box<Error>>;
}

pub struct RandomNear<'a> {
    pub near: &'a types::ZoneTile,
    pub tile: &'a types::ZoneTile,
    pub probability: u32,
}

pub struct Overflow {
    pub world_tile: world_types::WorldTile,
    pub default_tile: types::ZoneTile,
    pub depth: u32,
}

pub struct DefaultGenerator<'a> {
    pub world: &'a world::World<'a>,
    pub default_tile: &'a types::ZoneTile,
    pub random: Option<Vec<(f64, &'a types::ZoneTile)>>,
    pub random_near: Option<Vec<RandomNear<'a>>>,
    pub allow_overflow: Option<Vec<Overflow>>,
}

fn is_in_border(
    width: i32,
    height: i32,
    tested_row_i: i32,
    tested_col_i: i32,
    maximum_spacing: i32,
) -> Option<Border> {
    let row_part_len = (width - 1) / 3;
    let col_part_len = (height - 1) / 3;
    let tested_is_out_zone = is_out_zone(width, height, tested_row_i, tested_col_i);

    // Test is on top
    if tested_col_i >= row_part_len
        && tested_col_i < (width - row_part_len)
        && tested_row_i < maximum_spacing
    {
        return Some(Border::Top((tested_row_i + 1) as u32));
    }

    // Test is on top left
    if tested_col_i <= row_part_len
        && tested_row_i <= col_part_len
        && !tested_is_out_zone
        && tested_row_i < col_part_len
    {
        let spacing = tested_col_i - (row_part_len - tested_row_i - 1);
        if spacing <= maximum_spacing {
            return Some(Border::TopLeft(spacing as u32));
        }
    }

    // Test is on top right
    if tested_col_i >= (width - row_part_len) && tested_row_i < col_part_len && !tested_is_out_zone
    {
        let spacing = (width - tested_col_i) - (row_part_len - tested_row_i);
        if spacing <= maximum_spacing {
            return Some(Border::TopRight(spacing as u32));
        }
    }

    // Test is on left
    if tested_row_i >= col_part_len
        && tested_row_i < (height - col_part_len)
        && tested_col_i < maximum_spacing
    {
        return Some(Border::Left((tested_col_i + 1) as u32));
    }

    // Test is on right
    if tested_col_i >= (width - row_part_len)
        && tested_row_i <= (height - col_part_len)
        && !tested_is_out_zone
        && tested_row_i < (height - col_part_len)
        && (width - tested_col_i) <= maximum_spacing
    {
        return Some(Border::Right((width - tested_col_i) as u32));
    }

    // Test is bottom left
    if tested_row_i >= (height - col_part_len) && tested_col_i < row_part_len && !tested_is_out_zone
    {
        let spacing = tested_col_i + 1 - (row_part_len - (height - (tested_row_i + 1)));
        if spacing <= maximum_spacing {
            return Some(Border::BottomLeft(spacing as u32));
        }
    }

    // Test is bottom
    if tested_col_i >= row_part_len
        && tested_col_i < (width - row_part_len)
        && (height - tested_row_i) <= maximum_spacing
    {
        return Some(Border::Bottom((height - tested_row_i) as u32));
    }

    // Test is bottom right
    if tested_row_i >= (height - col_part_len)
        && tested_col_i >= (width - row_part_len)
        && !tested_is_out_zone
    {
        let spacing = (width - row_part_len + height - (tested_row_i + 1)) - tested_col_i;
        if spacing <= maximum_spacing {
            return Some(Border::BottomRight(spacing as u32));
        }
    }

    None
}

fn is_out_zone(width: i32, height: i32, tested_row_i: i32, tested_col_i: i32) -> bool {
    let row_part_len = (width - 1) / 3;
    let col_part_len = (height - 1) / 3;

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

fn fill_with_random_nears(random_nears: &Vec<RandomNear>, chars: &mut Vec<Vec<char>>) -> bool {
    let mut rng = thread_rng();
    for random_near in random_nears.into_iter() {
        let searched_char = types::get_char_for_tile(random_near.near);
        if is_there_around(searched_char, &chars) {
            let random: f64 = rng.gen();
            let probability: f64 = random_near.probability as f64 / 100.0;
            if random <= probability {
                let tile_char = types::get_char_for_tile(random_near.tile);
                chars.last_mut().unwrap().push(tile_char);
                return true;
            }
        }
    }

    false
}

fn get_world_tile<'a>(
    world: &'a World,
    zone_row_i: u32,
    zone_col_i: u32,
) -> Option<&'a world_types::WorldTile> {
    if zone_row_i > (world.rows.len() as u32) - 1 {
        return None;
    }

    if zone_col_i > (world.rows.first().unwrap().len() as u32) - 1 {
        return None;
    }

    Some(world.rows[zone_row_i as usize][zone_col_i as usize])
}

fn get_near_zone<'a>(
    world: &'a World,
    border: Border,
    ref_row_i: u32,
    ref_col_i: u32,
) -> Option<&'a world_types::WorldTile> {
    if ref_row_i == 0 && ref_col_i == 0 {
        match border {
            Border::Right(_) => return get_world_tile(world, ref_row_i, ref_col_i + 1),
            Border::Bottom(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i),
            Border::BottomRight(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i + 1),
            _ => return None,
        }
    } else if ref_row_i == 0 {
        match border {
            Border::Left(_) => return get_world_tile(world, ref_row_i, ref_col_i - 1),
            Border::Right(_) => return get_world_tile(world, ref_row_i, ref_col_i + 1),
            Border::BottomLeft(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i - 1),
            Border::Bottom(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i),
            Border::BottomRight(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i + 1),
            _ => return None,
        }
    } else if ref_col_i == 0 {
        match border {
            Border::Top(_) => return get_world_tile(world, ref_row_i - 1, ref_col_i),
            Border::TopRight(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i + 1),
            Border::Right(_) => return get_world_tile(world, ref_row_i, ref_col_i + 1),
            Border::Bottom(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i),
            Border::BottomRight(_) => return get_world_tile(world, ref_row_i + 1, ref_col_i + 1),
            _ => return None,
        }
    }

    match border {
        Border::TopLeft(_) => get_world_tile(world, ref_row_i - 1, ref_col_i - 1),
        Border::Top(_) => get_world_tile(world, ref_row_i - 1, ref_col_i),
        Border::TopRight(_) => get_world_tile(world, ref_row_i + 1, ref_col_i + 1),
        Border::Left(_) => get_world_tile(world, ref_row_i, ref_col_i - 1),
        Border::Right(_) => get_world_tile(world, ref_row_i, ref_col_i + 1),
        Border::BottomLeft(_) => get_world_tile(world, ref_row_i + 1, ref_col_i - 1),
        Border::Bottom(_) => get_world_tile(world, ref_row_i + 1, ref_col_i),
        Border::BottomRight(_) => get_world_tile(world, ref_row_i + 1, ref_col_i + 1),
    }
}

impl<'a> ZoneGenerator<'a> for DefaultGenerator<'a> {
    fn generate(
        &self,
        target: &'a Path,
        width: u32,
        height: u32,
        zone_row_i: u32,
        zone_col_i: u32,
    ) -> Result<(), Box<Error>> {
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
                    let mut push_with_near = true;
                    let border =
                        is_in_border(width as i32, height as i32, row_i as i32, col_i as i32, 2);

                    if border.is_some() && self.allow_overflow.is_some() {
                        let near_zone: Option<&world_types::WorldTile> =
                            get_near_zone(&self.world, border.unwrap(), zone_row_i, zone_col_i);
                        if near_zone.is_some() {
                            for allowed_overflow in self.allow_overflow.as_ref().unwrap().iter() {
                                if near_zone.unwrap() == &allowed_overflow.world_tile {
                                    let tile_char: char =
                                        types::get_char_for_tile(&allowed_overflow.default_tile);
                                    chars.last_mut().unwrap().push(tile_char);
                                    push_with_random = false;
                                    push_with_near = false;
                                    break;
                                }
                            }
                        }
                    }

                    if push_with_near && self.random_near.is_some() {
                        push_with_random =
                            !fill_with_random_nears(self.random_near.as_ref().unwrap(), &mut chars);
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
        let mut final_string_formated = String::from("::GEO\n");
        final_string_formated.push_str(&final_string);
        zone_file.write_all(final_string_formated.as_bytes())?;

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

    #[test]
    fn is_in_border_ok() {
        assert_eq!(None, is_in_border(7, 7, 0, 0, 2));
        assert_eq!(None, is_in_border(7, 7, 0, 1, 2));
        assert_eq!(Some(Border::Top(1)), is_in_border(7, 7, 0, 2, 2));
        assert_eq!(Some(Border::Top(1)), is_in_border(7, 7, 0, 3, 2));
        assert_eq!(Some(Border::Top(1)), is_in_border(7, 7, 0, 4, 2));
        assert_eq!(None, is_in_border(7, 7, 0, 5, 2));
        assert_eq!(None, is_in_border(7, 7, 0, 6, 2));

        assert_eq!(None, is_in_border(7, 7, 1, 0, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(7, 7, 1, 1, 2));
        assert_eq!(Some(Border::Top(2)), is_in_border(7, 7, 1, 2, 2));
        assert_eq!(Some(Border::Top(2)), is_in_border(7, 7, 1, 3, 2));
        assert_eq!(Some(Border::Top(2)), is_in_border(7, 7, 1, 4, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(7, 7, 1, 5, 2));
        assert_eq!(None, is_in_border(7, 7, 1, 6, 2));

        assert_eq!(Some(Border::Left(1)), is_in_border(7, 7, 2, 0, 2));
        assert_eq!(Some(Border::Left(2)), is_in_border(7, 7, 2, 1, 2));
        assert_eq!(None, is_in_border(7, 7, 2, 2, 2));
        assert_eq!(None, is_in_border(7, 7, 2, 3, 2));
        assert_eq!(None, is_in_border(7, 7, 2, 4, 2));
        assert_eq!(Some(Border::Right(2)), is_in_border(7, 7, 2, 5, 2));
        assert_eq!(Some(Border::Right(1)), is_in_border(7, 7, 2, 6, 2));

        assert_eq!(Some(Border::Left(1)), is_in_border(7, 7, 3, 0, 2));
        assert_eq!(Some(Border::Left(2)), is_in_border(7, 7, 3, 1, 2));
        assert_eq!(None, is_in_border(7, 7, 3, 2, 2));
        assert_eq!(None, is_in_border(7, 7, 3, 3, 2));
        assert_eq!(None, is_in_border(7, 7, 3, 4, 2));
        assert_eq!(Some(Border::Right(2)), is_in_border(7, 7, 3, 5, 2));
        assert_eq!(Some(Border::Right(1)), is_in_border(7, 7, 3, 6, 2));

        assert_eq!(Some(Border::Left(1)), is_in_border(7, 7, 4, 0, 2));
        assert_eq!(Some(Border::Left(2)), is_in_border(7, 7, 4, 1, 2));
        assert_eq!(None, is_in_border(7, 7, 4, 2, 2));
        assert_eq!(None, is_in_border(7, 7, 4, 3, 2));
        assert_eq!(None, is_in_border(7, 7, 4, 4, 2));
        assert_eq!(Some(Border::Right(2)), is_in_border(7, 7, 4, 5, 2));
        assert_eq!(Some(Border::Right(1)), is_in_border(7, 7, 4, 6, 2));

        assert_eq!(None, is_in_border(7, 7, 5, 0, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(7, 7, 5, 1, 2));
        assert_eq!(Some(Border::Bottom(2)), is_in_border(7, 7, 5, 2, 2));
        assert_eq!(Some(Border::Bottom(2)), is_in_border(7, 7, 5, 3, 2));
        assert_eq!(Some(Border::Bottom(2)), is_in_border(7, 7, 5, 4, 2));
        assert_eq!(Some(Border::BottomRight(1)), is_in_border(7, 7, 5, 5, 2));
        assert_eq!(None, is_in_border(7, 7, 5, 6, 2));

        assert_eq!(None, is_in_border(7, 7, 6, 0, 2));
        assert_eq!(None, is_in_border(7, 7, 6, 1, 2));
        assert_eq!(Some(Border::Bottom(1)), is_in_border(7, 7, 6, 2, 2));
        assert_eq!(Some(Border::Bottom(1)), is_in_border(7, 7, 6, 3, 2));
        assert_eq!(Some(Border::Bottom(1)), is_in_border(7, 7, 6, 4, 2));
        assert_eq!(None, is_in_border(7, 7, 6, 5, 2));
        assert_eq!(None, is_in_border(7, 7, 6, 6, 2));

        assert_eq!(Some(Border::Top(1)), is_in_border(23, 23, 0, 7, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(23, 23, 1, 6, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(23, 23, 2, 5, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(23, 23, 3, 4, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(23, 23, 4, 3, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(23, 23, 5, 2, 2));
        assert_eq!(Some(Border::TopLeft(1)), is_in_border(23, 23, 6, 1, 2));
        assert_eq!(Some(Border::Left(1)), is_in_border(23, 23, 7, 0, 2));
        assert_eq!(None, is_in_border(23, 23, 6, 7, 2));

        assert_eq!(Some(Border::Top(1)), is_in_border(23, 23, 0, 15, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(23, 23, 1, 16, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(23, 23, 2, 17, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(23, 23, 3, 18, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(23, 23, 4, 19, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(23, 23, 5, 20, 2));
        assert_eq!(Some(Border::TopRight(1)), is_in_border(23, 23, 6, 21, 2));
        assert_eq!(Some(Border::Right(1)), is_in_border(23, 23, 7, 22, 2));

        assert_eq!(None, is_in_border(23, 23, 7, 20, 2));

        assert_eq!(Some(Border::Left(1)), is_in_border(23, 23, 15, 0, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(23, 23, 16, 1, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(23, 23, 17, 2, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(23, 23, 18, 3, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(23, 23, 19, 4, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(23, 23, 20, 5, 2));
        assert_eq!(Some(Border::BottomLeft(1)), is_in_border(23, 23, 21, 6, 2));
        assert_eq!(Some(Border::Bottom(1)), is_in_border(23, 23, 22, 7, 2));

        assert_eq!(Some(Border::Right(1)), is_in_border(23, 23, 15, 22, 2));
        assert_eq!(
            Some(Border::BottomRight(1)),
            is_in_border(23, 23, 16, 21, 2)
        );
        assert_eq!(
            Some(Border::BottomRight(1)),
            is_in_border(23, 23, 17, 20, 2)
        );
        assert_eq!(
            Some(Border::BottomRight(1)),
            is_in_border(23, 23, 18, 19, 2)
        );
        assert_eq!(
            Some(Border::BottomRight(1)),
            is_in_border(23, 23, 19, 18, 2)
        );
        assert_eq!(
            Some(Border::BottomRight(1)),
            is_in_border(23, 23, 20, 17, 2)
        );
        assert_eq!(
            Some(Border::BottomRight(1)),
            is_in_border(23, 23, 21, 16, 2)
        );
        assert_eq!(Some(Border::Bottom(1)), is_in_border(23, 23, 22, 15, 2));
    }
}
