
def main():
    mapping = {
        2: 'a',
        3: 'b',
        4: 'd',
        5: 'l',
        6: 'n',
        7: 'p',
        8: 'r',
        9: 't',
        10: 'u',
    }

    reverse_mapping = {
        y: x for x, y in mapping.items()
    }

    for x in [7, 6, 4, 10, 5, 3, 4, 5, 9, 6, 5, 8]:
        print(mapping[x])

    print('done')


if __name__ == '__main__':
    main()