use crate::RollingError;

#[derive(PartialEq, Debug)]
pub enum WorldTile {
    Sea,
    Mountain,
    Beach,
    Plain,
    Jungle,
    Hill,
}

pub fn get_type(search_id: &str) -> Result<WorldTile, RollingError> {
    match search_id {
        "SEA" => Ok(WorldTile::Sea),
        "MOUNTAIN" => Ok(WorldTile::Mountain),
        "BEACH" => Ok(WorldTile::Beach),
        "PLAIN" => Ok(WorldTile::Plain),
        "JUNGLE" => Ok(WorldTile::Jungle),
        "HILL" => Ok(WorldTile::Hill),
        _ => Err(RollingError::new(format!(
            "No world tile found for id \"{}\"",
            search_id
        ))),
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn get_type_ok_sea() {
        let result = get_type("SEA");
        assert_eq!(WorldTile::Sea, result.unwrap())
    }

    #[test]
    #[should_panic]
    fn get_type_err_unknown() {
        get_type("UNKNOWN").unwrap();
    }
}
