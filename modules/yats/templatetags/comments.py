# -*- coding: utf-8 -*-
from django.template import Library

register = Library()

# 0 = nothing, 1 = close, 2 = reopen, 3 = ref, 4 = ticket changed, 5 = file added, 6 = comment added, 7 = reassign

def comment_color(value):
    result = {
      0: lambda : 'info',
      1: lambda : 'danger',
      2: lambda : 'success',
      3: lambda : 'inverse',
      4: lambda : 'warning',
      5: lambda : '',
      6: lambda : 'primary',
      7: lambda : 'warning',
      8: lambda : 'danger',
      9: lambda : 'info',
      10: lambda : 'warning',
      11: lambda : 'warning',
    }[value]()
    return result

register.filter('comment_color', comment_color)

def history_icon(value):
    result = {
      0: lambda : '',
      1: lambda : 'fa-check',
      2: lambda : 'fa-undo',
      3: lambda : 'fa-link',
      4: lambda : 'fa-pencil-square-o',
      5: lambda : 'fa-file',
      6: lambda : 'fa-comment',
      7: lambda : 'fa-user',
      8: lambda : 'fa-trash',
      9: lambda : 'fa-check-square',
      10: lambda : 'fa-clock-o',
      11: lambda : 'fa-cogs',
    }[value]()
    return result

register.filter('history_icon', history_icon)
