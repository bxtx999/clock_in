from sign import main, get_config, schedule


if __name__ == '__main__':
    main(**get_config())
    try:
        schedule().start()
    except (KeyboardInterrupt, SystemExit):
        pass
    exit()
