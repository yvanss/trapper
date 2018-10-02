#!/usr/bin/python
import os
import re
import pandas
import datetime
from optparse import OptionParser, make_option


class DepMeta(object):

    def __init__(
            self, media_root, outfile='./deploments_metadata.csv' 
    ):
        if not os.path.isdir(media_root):
            raise Exception('There is no directory: %s' % media_root)
        else:
            self.media_root = media_root
        self.outfile = outfile


    def handle(self):
        data = {
            'deployment_id': [],
            'deployment_start': [],
            'deployment_end': [],
        }
        for root, dirnames, filenames in os.walk(self.media_root):
            if not filenames:
                continue
            rdates = []
            data['deployment_id'].append(os.path.basename(root))
            for filename in filenames:
                rdates.append(
                    datetime.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.join(root, filename)
                        )
                    )
                )
            data['deployment_start'].append(min(rdates))
            data['deployment_end'].append(max(rdates))
        pandas.DataFrame(
            data, columns=[
                'deployment_id', 'deployment_start', 'deployment_end'
            ]
        ).to_csv(self.outfile)


def main():
    title = 'Generates a table with deployments start/end datetimes; based on control records (the first and the last one)'
    usage = 'Usage: %prog [options] media_root'
    option_list = [
        make_option(
            '--outfile',
            action='store',
            dest='outfile',
            default='./deployments_metadata.csv',
            help='Name of the output csv file'
        ),
    ]
    parser = OptionParser(usage, option_list=option_list)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Incorrect number of arguments.")
        
    cm = DepMeta(
        media_root=args[0],
        outfile=options.outfile
    ).handle()


if __name__ == "__main__":
    main()


        
