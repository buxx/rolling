use super::types;
use crate::util;
use crate::RollingError;
use std::collections::HashMap;

fn get_tile_type_from_raw(raw_line: &str) -> Result<(char, types::WorldTile), RollingError> {
    // TODO BS 2019-04-03: Strip the line ?
    let tile_info: Vec<&str> = raw_line.split_whitespace().collect();
    assert_eq!(2, tile_info.len());

    let tile_char = tile_info[0].chars().next().unwrap();
    let tile_type_id = &tile_info[1].replace("*", "");
    let tile_type = match types::get_type(tile_type_id) {
        Ok(tile_type) => tile_type,
        Err(_e) => return Err(RollingError::new(format!("Unknown tile {}", tile_type_id))),
    };

    Ok((tile_char, tile_type))
}

pub struct WorldMapLegend {
    pub default: types::WorldTile,
    pub tiles: HashMap<char, types::WorldTile>,
}

impl WorldMapLegend {
    pub fn new(source: &String) -> Result<WorldMapLegend, RollingError> {
        let mut tiles: HashMap<char, types::WorldTile> = HashMap::new();
        let legend_source = match util::extract_block_from_source(util::BLOCK_LEGEND, &source) {
            Ok(source) => source,
            Err(e) => {
                return Err(RollingError::new(format!(
                    "Error during extraction of legend: {}",
                    e.message
                )));
            }
        };

        for line in legend_source.split("\n") {
            let (tile_char, tile_type) = match get_tile_type_from_raw(line) {
                Ok(tile_infos) => tile_infos,
                Err(e) => return Err(e),
            };
            tiles.insert(tile_char, tile_type);
        }

        Ok(WorldMapLegend {
            default: types::WorldTile::Sea,
            tiles,
        })
    }

    pub fn get_type(&self, raw_str: char) -> Result<&types::WorldTile, RollingError> {
        match self.tiles.get(&raw_str) {
            Some(v) => Ok(v),
            None => Err(RollingError::new(format!(
                "No world tile match with {}",
                raw_str
            ))),
        }
    }
}
