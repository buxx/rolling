# coding: utf-8
import argparse


def run(args: argparse.Namespace) -> None:
    print(args.server_address)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Start Rolling interface'
    )
    parser.add_argument(
        '--server-address',
        type=str,
        help='Game server address'
    )

    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()
