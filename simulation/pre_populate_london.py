from simulation import sim_classes


def main():
    lc = sim_classes.LondonCreator()
    lc.create_london_from_scratch()
    lc.pickle_city('simulation/tests/files/test2.pickle')


if __name__ == "__main__":
    main()