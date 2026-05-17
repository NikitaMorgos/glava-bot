#!/bin/bash
cd /opt/glava
git config user.email 'cursor@glava.bot'
git config user.name 'Cursor'
git -c trailer.ifexists=doNothing commit -m 'chore: add v53 run artifacts + update task 031'
git push -u origin feat/v53-artifacts
