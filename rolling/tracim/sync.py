import argparse
import configparser

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

    server_config_reader = configparser.ConfigParser()
    server_config_reader.read(args.server_config_file_path)
    tracim_api_key = server_config_reader["tracim"]["api_key"]
    tracim_api_address = server_config_reader["tracim"]["api_address"]
    tracim_admin_email = server_config_reader["tracim"]["admin_email"]
    tracim_config = rrolling.Config(
        api_key=rrolling.ApiKey(tracim_api_key),
        api_address=rrolling.ApiAddress(tracim_api_address),
        admin_email=rrolling.Email(tracim_admin_email),
    )

    config = ServerConfig.from_config_file_path(args.server_config_file_path)
    kernel = Kernel(server_config=config)
    kernel.init_server_db_session()

    print("Synchronize all existing character with Tracim account")
    for character_id in kernel.character_lib.get_all_character_ids(alive=True):
        character_doc = kernel.character_lib.get_document(character_id)
        account = kernel.account_lib.get_account_for_id(character_doc.account_id)
        # FIXME BS NOW : normalize (limit username at azAz ...)
        tracim_account = rrolling.Account(
            username=rrolling.Username(character_doc.name),
            password=rrolling.Password(character_doc.tracim_password),
            email=rrolling.Email(account.email),
        )
        tracim_user_id = rrolling.Dealer(tracim_config).ensure_account(tracim_account)
        character_doc.tracim_user_id = tracim_user_id
        kernel.server_db_session.add(character_doc)
        print(f"{character_id} -> {tracim_user_id}")

    kernel.server_db_session.commit()

    print("Ensure personal space of characters")
    for character_id in kernel.character_lib.get_all_character_ids(alive=True):
        character_doc = kernel.character_lib.get_document(character_id)
        space_name = f"🏠 Journal personnel de {character_doc.name}"
        tracim_home_space_id = rrolling.Dealer(tracim_config).ensure_space(
            rrolling.SpaceName(space_name)
        )
        rrolling.Dealer(tracim_config).ensure_space_role(
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
