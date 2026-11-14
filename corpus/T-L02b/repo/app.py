from payroll import core, reports

DEMO = [("K-1", 2, 2050), ("K-2", 1, 640)]


def main():
    print("demo total:", core.total(DEMO))
    print("demo report:", reports.summarise(DEMO))


if __name__ == "__main__":
    main()
