from wintoucher import Dots, WintoucherApp  # noqa: F401


def main():
    app = WintoucherApp(dots=Dots())
    app.run()


if __name__ == "__main__":
    main()
