use crate::tile::world::legend::WorldMapLegend;
use crate::tile::world::types;
use crate::util;
use crate::RollingError;

pub struct World<'a> {
    pub legend: &'a WorldMapLegend,
    pub rows: Vec<Vec<&'a types::WorldTile>>,
    pub geo_chars: Vec<Vec<char>>,
}

impl<'a> World<'a> {
    pub fn new<'b>(source: &String, legend: &'b WorldMapLegend) -> Result<World<'b>, RollingError> {
        let geo_source = match util::extract_block_from_source(util::BLOCK_GEO, &source) {
            Ok(source) => source,
            Err(e) => return Err(e),
        };
        let mut rows: Vec<Vec<&types::WorldTile>> = Vec::new();
        let mut geo_chars: Vec<Vec<char>> = Vec::new();

        for line in geo_source.lines() {
            let mut row: Vec<&types::WorldTile> = Vec::new();
            let mut row_chars: Vec<char> = Vec::new();
            for raw_char in line.chars() {
                let world_tile = match legend.get_type(raw_char) {
                    Ok(world_tile) => world_tile,
                    Err(e) => return Err(e),
                };
                row.push(world_tile);
                row_chars.push(raw_char);
            }
            rows.push(row);
            geo_chars.push(row_chars);
        }

        Ok(World {
            legend,
            rows,
            geo_chars,
        })
    }
}
