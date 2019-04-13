pub enum ZoneTile {
    SaltedWater,
    Sand,
    Rock,
    RockyGround,
    DryBush,
    ShortGrass,
}

pub fn get_char_for_tile(tile: &ZoneTile) -> char {
    match tile {
        ZoneTile::SaltedWater => '~',
        ZoneTile::Sand => '⡩',
        ZoneTile::Rock => '#',
        ZoneTile::DryBush => 'ൖ',
        ZoneTile::RockyGround => '⑉',
        ZoneTile::ShortGrass => '⁘',
    }
}
