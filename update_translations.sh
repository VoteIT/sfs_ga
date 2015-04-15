 #!/bin/bash
 #You need lingua and gettext installed to run this
 
 echo "Updating sfs_ga.pot"
 pot-create -d sfs_ga -o sfs_ga/locale/sfs_ga.pot .
 echo "Merging Swedish localisation"
 msgmerge --update sfs_ga/locale/sv/LC_MESSAGES/sfs_ga.po sfs_ga/locale/sfs_ga.pot
 echo "Updated locale files"
 