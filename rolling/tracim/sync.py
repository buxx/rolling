import argparse
from rolling.exception import CharacterHaveNoAccountId

from rolling.kernel import Kernel, ServerConfig
import rrolling


def main():
    parser = argparse.ArgumentParser(description="Start Rolling interface")
    parser.add_argument(
        "server_config_file_path",
        type=str,
        help="server config file path",
        default="./server.ini",
    )
    args = parser.parse_args()
    config = ServerConfig.from_config_file_path(args.server_config_file_path)
    kernel = Kernel(server_config=config)
    kernel.init_server_db_session()

    print("Synchronize all existing character with Tracim account")
    for character_id in kernel.character_lib.get_all_character_ids(alive=True):
        character_doc = kernel.character_lib.get_document(character_id)
        try:
            tracim_account = kernel.character_lib.get_tracim_account(character_id)
        except CharacterHaveNoAccountId:
            print(f"  ❌ {character_doc.name} -> ERROR (no account_id)")
            continue

        try:
            tracim_user_id = rrolling.tracim.Dealer(
                config.tracim_config
            ).ensure_account(tracim_account)
        except Exception as exc:
            print(f"  ❌ {character_doc.name} -> ERROR ({exc})")
            continue

        character_doc.tracim_user_id = tracim_user_id
        kernel.server_db_session.add(character_doc)
        print(f"  ✅ {character_doc.name} -> {tracim_user_id}")

    print()
    kernel.server_db_session.commit()

    print("Ensure personal space of characters")
    for character_id in kernel.character_lib.get_all_character_ids(alive=True):
        character_doc = kernel.character_lib.get_document(character_id)
        space_name = kernel.character_lib.character_home_space_name(character_doc)

        if character_doc.tracim_user_id is None:
            print(f"  ❌ {character_doc.name} -> ERROR (no tracim_user_id)")
            continue

        try:
            tracim_home_space_id = rrolling.tracim.Dealer(
                config.tracim_config
            ).ensure_space(rrolling.tracim.SpaceName(space_name))
        except Exception as exc:
            print(f"  ❌ {character_doc.name} -> ERROR ({exc})")
            continue

        try:
            rrolling.tracim.Dealer(config.tracim_config).ensure_space_role(
                rrolling.tracim.SpaceId(tracim_home_space_id),
                rrolling.tracim.AccountId(character_doc.tracim_user_id),
                "reader",
            )
        except Exception as exc:
            print(f"  ❌ {character_doc.name} -> ERROR ({exc})")
            continue

        character_doc.tracim_home_space_id = tracim_home_space_id
        kernel.server_db_session.add(character_doc)
        print(f"  ✅ {character_doc.name} -> {tracim_home_space_id} (reader)")

    for space_id, role in kernel.server_config.tracim_common_spaces:
        print(f"Ensure common space {space_id} ({role}) of characters")
        for character_id in kernel.character_lib.get_all_character_ids(alive=True):
            character_doc = kernel.character_lib.get_document(character_id)
            if character_doc.tracim_user_id is None:
                print(f"  ❌ {character_doc.name} -> ERROR (no tracim_user_id)")
                continue

            try:
                rrolling.tracim.Dealer(config.tracim_config).ensure_space_role(
                    rrolling.tracim.SpaceId(space_id),
                    rrolling.tracim.AccountId(character_doc.tracim_user_id),
                    role,
                )
            except Exception as exc:
                print(f"  ❌ {character_doc.name} -> ERROR ({exc})")
                continue

            kernel.server_db_session.add(character_doc)
            print(f"  ✅ {character_doc.name} -> {tracim_home_space_id} ({role})")

    print()
    kernel.server_db_session.commit()

    print("Ensure affinities spaces and roles")
    for affinity in kernel.affinity_lib.get_all():
        try:
            space_id = rrolling.tracim.Dealer(config.tracim_config).ensure_space(
                rrolling.tracim.SpaceName(
                    kernel.affinity_lib.affinity_space_name(affinity)
                ),
            )
        except Exception as exc:
            print(f"  ❌ {affinity.name} -> ERROR ({exc})")
            continue

        affinity.tracim_space_id = space_id
        kernel.server_db_session.add(affinity)
        kernel.server_db_session.commit()
        print(f"  ✅ {affinity.name} -> {space_id}")

        chief_character_id = kernel.affinity_lib.get_chief_of_affinity(
            affinity.id
        ).character_id
        chief_character_doc = kernel.character_lib.get_document(chief_character_id)
        if chief_character_doc.tracim_user_id is None:
            print(f"  ❌ {chief_character_doc.name} -> ERROR (no tracim_user_id)")
            continue

        try:
            rrolling.tracim.Dealer(config.tracim_config).ensure_space_role(
                rrolling.tracim.SpaceId(space_id),
                rrolling.tracim.AccountId(chief_character_doc.tracim_user_id),
                "contributor",
            )
        except Exception as exc:
            print(f"  ❌ {chief_character_doc.name} -> ERROR ({exc})")
            continue

        kernel.server_db_session.add(character_doc)
        print(f"    ✅ {chief_character_doc.name} -> {space_id} (contributor)")

        for character_id in kernel.affinity_lib.get_members_ids(
            affinity_id=affinity.id,
            exclude_character_ids=[chief_character_id],
        ):
            character_doc = kernel.character_lib.get_document(character_id)
            if character_doc.tracim_user_id is None:
                print(f"  ❌ {character_doc.name} -> ERROR (no tracim_user_id)")
                continue

            try:
                rrolling.tracim.Dealer(config.tracim_config).ensure_space_role(
                    rrolling.tracim.SpaceId(space_id),
                    rrolling.tracim.AccountId(character_doc.tracim_user_id),
                    "contributor",
                )
            except Exception as exc:
                print(f"  ❌ {character_doc.name} -> ERROR ({exc})")
                continue

            kernel.server_db_session.add(character_doc)
            print(f"    ✅ {character_doc.name} -> {space_id} (contributor)")

        # FIXME BS NOW :
        # * Sur page du compte : des liens pour afficher tracim avec les persos mort

    print()
    kernel.server_db_session.commit()


if __name__ == "__main__":
    main()
