pub enum ZoneTile {
    SaltedWater,
    Sand,
    Rock,
    RockyGround,
    DryBush,
    ShortGrass,
    HightGrass,
    Dirt,
    LeafTree,
    TropicalTree,
    DeadTree,
    FreshWater,
}

pub fn get_char_for_tile(tile: &ZoneTile) -> char {
    match tile {
        ZoneTile::SaltedWater => '~',
        ZoneTile::Sand => '⡩',
        ZoneTile::Rock => '#',
        ZoneTile::DryBush => 'ʛ',
        ZoneTile::RockyGround => '፨',
        ZoneTile::ShortGrass => '܄',
        ZoneTile::HightGrass => '؛',
        ZoneTile::Dirt => '⁖',
        ZoneTile::LeafTree => '߉',
        ZoneTile::TropicalTree => 'ፆ',
        ZoneTile::DeadTree => 'آ',
        ZoneTile::FreshWater => 'ގ',
    }
}
