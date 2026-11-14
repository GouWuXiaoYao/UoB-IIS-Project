from ticketing import core, reports

DEMO = [("K-1", 2, 1899), ("K-2", 1, 725)]


def main():
    print("demo total:", core.total(DEMO))
    print("demo report:", reports.summarise(DEMO))


if __name__ == "__main__":
    main()
