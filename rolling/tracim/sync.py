import argparse

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
        tracim_account = kernel.character_lib.get_tracim_account(character_id)
        tracim_user_id = rrolling.Dealer(config.tracim_config).ensure_account(
            tracim_account
        )
        character_doc.tracim_user_id = tracim_user_id
        kernel.server_db_session.add(character_doc)
        print(f"{character_id} -> {tracim_user_id}")

    kernel.server_db_session.commit()

    print("Ensure personal space of characters")
    for character_id in kernel.character_lib.get_all_character_ids(alive=True):
        character_doc = kernel.character_lib.get_document(character_id)
        space_name = kernel.character_lib.character_home_space_name(character_doc)
        tracim_home_space_id = rrolling.Dealer(config.tracim_config).ensure_space(
            rrolling.SpaceName(space_name)
        )
        rrolling.Dealer(config.tracim_config).ensure_space_role(
            rrolling.SpaceId(tracim_home_space_id),
            rrolling.AccountId(character_doc.tracim_user_id),
            "reader",
        )
        character_doc.tracim_home_space_id = tracim_home_space_id
        kernel.server_db_session.add(character_doc)
        print(f"{character_id} -> {tracim_home_space_id} (reader)")

    kernel.server_db_session.commit()


if __name__ == "__main__":
    main()
