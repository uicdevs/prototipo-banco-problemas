from gluon import current, SQLFORM, FORM
from gluon import XML
from gluon._compat import reduce, integer_types, iteritems
from gluon.html import truncate_string, XmlComponent, HTML, URL, DIV, CAT, INPUT, TH, TR, TD, UL, COL, TABLE, OPTION, SELECT, SCRIPT
from gluon.sqlhtml import ExporterCSV_hidden, ExporterCSV, ExporterXML, ExporterHTML, ExporterJSON, ExporterTSV_hidden, \
    ExporterTSV, safe_int, CacheRepresenter



import datetime
import re
import copy

import os
from gluon._compat import iteritems, integer_types
from gluon.http import HTTP, redirect
from gluon.html import XmlComponent, truncate_string
from gluon.html import XML, SPAN, A, DIV, CAT, UL, LI
from gluon.html import FORM, INPUT, COL, COLGROUP
from gluon.html import TABLE, THEAD, TBODY, TR, TD, TH
from gluon.html import URL
from pydal.objects import Table, Row, Expression, Field, Set, Rows
from pydal.helpers.methods import smart_query, bar_encode, _repr_ref, merge_tablemaps
from pydal.helpers.classes import Reference, SQLCustomType

from gluon.globals import current
from functools import reduce

try:
    import gluon.settings as settings
except ImportError:
    settings = {}

widget_class = re.compile('^\w*')

REGEX_ALIAS_MATCH = re.compile('^(.*) AS (.*)$')


class Grid:

    @staticmethod
    def search_menu(fields,
                    search_options=None,
                    prefix='w2p'
                    ):
        T = current.T
        panel_id = '%s_query_panel' % prefix
        fields_id = '%s_query_fields' % prefix
        keywords_id = '%s_keywords' % prefix
        field_id = '%s_field' % prefix
        value_id = '%s_value' % prefix
        search_options = search_options or {
            'string': ['=', '!=', '<', '>', '<=', '>=', 'starts with', 'contains', 'in', 'not in'],
            'text': ['=', '!=', '<', '>', '<=', '>=', 'starts with', 'contains', 'in', 'not in'],
            'date': ['=', '!=', '<', '>', '<=', '>='],
            'time': ['=', '!=', '<', '>', '<=', '>='],
            'datetime': ['=', '!=', '<', '>', '<=', '>='],
            'integer': ['=', '!=', '<', '>', '<=', '>=', 'in', 'not in'],
            'double': ['=', '!=', '<', '>', '<=', '>='],
            'id': ['=', '!=', '<', '>', '<=', '>=', 'in', 'not in'],
            'reference': ['=', '!='],
            'boolean': ['=', '!=']}
        if fields[0]._db._adapter.dbengine == 'google:datastore':
            search_options['string'] = ['=', '!=', '<', '>', '<=', '>=']
            search_options['text'] = ['=', '!=', '<', '>', '<=', '>=']
            search_options['list:string'] = ['contains']
            search_options['list:integer'] = ['contains']
            search_options['list:reference'] = ['contains']
        criteria = []
        selectfields = []
        for field in fields:
            name = str(field).replace('.', '-')
            # treat ftype 'decimal' as 'double'
            # (this fixes problems but needs refactoring!
            if isinstance(field.type, SQLCustomType):
                ftype = field.type.type.split(' ')[0]
            else:
                ftype = field.type.split(' ')[0]
            if ftype.startswith('decimal'):
                ftype = 'double'
            elif ftype == 'bigint':
                ftype = 'integer'
            elif ftype.startswith('big-'):
                ftype = ftype[4:]
            # end
            options = search_options.get(ftype, None)
            if options:
                label = isinstance(
                    field.label, str) and T(field.label) or field.label
                selectfields.append(OPTION(label, _value=str(field)))
                # At web2py level SQLCustomType field values are treated as normal web2py types
                if isinstance(field.type, SQLCustomType):
                    field_type = field.type.type
                else:
                    field_type = field.type

                operators = SELECT(*[OPTION(T(option), _value=option) for option in options],
                                   _class='form-control')
                _id = "%s_%s" % (value_id, name)
                if field_type in ['boolean', 'double', 'time', 'integer']:
                    widget_ = SQLFORM.widgets[field_type]
                    value_input = widget_.widget(field, field.default, _id=_id,
                                                 _class=widget_._class + ' form-control')
                elif field_type == 'date':
                    iso_format = {'_data-w2p_date_format': '%Y-%m-%d'}
                    widget_ = SQLFORM.widgets.date
                    value_input = widget_.widget(field, field.default, _id=_id,
                                                 _class=widget_._class + ' form-control',
                                                 **iso_format)
                elif field_type == 'datetime':
                    iso_format = {'_data-w2p_datetime_format': '%Y-%m-%d %H:%M:%S'}
                    widget_ = SQLFORM.widgets.datetime
                    value_input = widget_.widget(field, field.default, _id=_id,
                                                 _class=widget_._class + ' form-control',
                                                 **iso_format)
                elif (field_type.startswith('integer') or
                      field_type.startswith('reference ') or
                      field_type.startswith('list:integer') or
                      field_type.startswith('list:reference ')):
                    widget_ = SQLFORM.widgets.integer
                    value_input = widget_.widget(
                        field, field.default, _id=_id,
                        _class=widget_._class + ' form-control')
                else:
                    value_input = INPUT(
                        _type='text', _id=_id,
                        _class="%s %s" % ((field_type or ''), 'form-control'))

                if hasattr(field.requires, 'options'):
                    value_input = SELECT(
                        *[OPTION(v, _value=k)
                          for k, v in field.requires.options()],
                        _class='form-control',
                        **dict(_id=_id))

                new_button = INPUT(
                    _type="button", _value=T('New Search'), _class="btn btn-default",
                    _title=T('Start building a new search'),
                    _onclick="%s_build_query('new','%s')" % (prefix, field))
                and_button = INPUT(
                    _type="button", _value=T('+ And'), _class="btn btn-default",
                    _title=T('Add this to the search as an AND term'),
                    _onclick="%s_build_query('and','%s')" % (prefix, field))
                or_button = INPUT(
                    _type="button", _value=T('+ Or'), _class="btn btn-default",
                    _title=T('Add this to the search as an OR term'),
                    _onclick="%s_build_query('or','%s')" % (prefix, field))
                close_button = INPUT(
                    _type="button", _value=T('Close'), _class="btn btn-default",
                    _onclick="jQuery('#%s').slideUp()" % panel_id)

                criteria.append(DIV(
                    operators, value_input, new_button,
                    and_button, or_button, close_button,
                    _id='%s_%s' % (field_id, name),
                    _class='w2p_query_row',
                    _style='display:none'))

        criteria.insert(0, SELECT(
            _id=fields_id,
            _onchange="jQuery('.w2p_query_row').hide();jQuery('#%s_'+jQuery('#%s').val().replace('.','-')).show();" % (
            field_id, fields_id),
            _style='float:left', _class='form-control',
            *selectfields))

        fadd = SCRIPT("""
            $.fn.changeVal = function (v) {
                return this.val(v).trigger("change");
            }
            jQuery('#%(fields_id)s input,#%(fields_id)s select').css(
                'width','auto');
            jQuery(function(){web2py_ajax_fields('#%(fields_id)s');});
            function %(prefix)s_build_query(aggregator,a) {
              var b=a.replace('.','-');
              var option = jQuery('#%(field_id)s_'+b+' select').val();
              var value;
              var $value_item = jQuery('#%(value_id)s_'+b);
              if ($value_item.is(':checkbox')){
                if  ($value_item.is(':checked'))
                        value = 'True';
                else  value = 'False';
              }
              else
              { value = $value_item.val().replace('"','\\\\"')}
              var s=a+' '+option+' "'+value+'"';
              var k=jQuery('#%(keywords_id)s');
              var v=k.val();
              if(aggregator=='new') k.val(s).trigger("change"); else k.val((v?(v+' '+ aggregator +' '):'')+s).trigger("change");
            }
            """ % dict(
            prefix=prefix, fields_id=fields_id, keywords_id=keywords_id,
            field_id=field_id, value_id=value_id
        )
                      )
        return CAT(
            DIV(_id=panel_id, _style="display:none;", *criteria), fadd)

    @staticmethod
    def grid(query,
             fields=None,
             field_id=None,
             left=None,
             headers={},
             orderby=None,
             groupby=None,
             searchable=True,
             sortable=True,
             paginate=20,
             deletable=True,
             editable=True,
             details=True,
             selectable=None,
             create=True,
             csv=True,
             links=None,
             links_in_grid=True,
             upload='<default>',
             args=[],
             user_signature=True,
             maxtextlengths={},
             maxtextlength=20,
             onvalidation=None,
             onfailure=None,
             oncreate=None,
             onupdate=None,
             ondelete=None,
             sorter_icons=(XML('&#x25B2;'), XML('&#x25BC;')),
             ui='web2py',
             showbuttontext=True,
             _class="web2py_grid",
             formname='web2py_grid',
             search_widget='default',
             advanced_search=True,
             ignore_rw=False,
             formstyle=None,
             exportclasses=None,
             formargs={},
             createargs={},
             editargs={},
             viewargs={},
             selectable_submit_button='Submit',
             buttons_placement='right',
             links_placement='right',
             noconfirm=False,
             cache_count=None,
             client_side_delete=False,
             ignore_common_filters=None,
             auto_pagination=True,
             use_cursor=False,
             represent_none=None,
             showblobs=False,
             table_class='table table-responsive-sm table-hover table-outline mb-0'):

        dbset = None
        formstyle = formstyle or current.response.formstyle
        if isinstance(query, Set):
            query = query.query

        # jQuery UI ThemeRoller classes (empty if ui is disabled)
        if ui == 'jquery-ui':
            ui = dict(widget='ui-widget',
                      header='ui-widget-header',
                      content='ui-widget-content',
                      default='ui-state-default',
                      cornerall='ui-corner-all',
                      cornertop='ui-corner-top',
                      cornerbottom='ui-corner-bottom',
                      button='ui-button-text-icon-primary',
                      buttontext='ui-button-text',
                      buttonadd='ui-icon ui-icon-plusthick',
                      buttonback='ui-icon ui-icon-arrowreturnthick-1-w',
                      buttonexport='ui-icon ui-icon-transferthick-e-w',
                      buttondelete='ui-icon ui-icon-trash',
                      buttonedit='ui-icon ui-icon-pencil',
                      buttontable='ui-icon ui-icon-triangle-1-e',
                      buttonview='ui-icon ui-icon-zoomin',
                      )
        elif ui == 'web2py':
            ui = dict(widget='',
                      header='',
                      content='',
                      default='',
                      cornerall='',
                      cornertop='',
                      cornerbottom='',
                      button='button btn btn-default btn-secondary',
                      buttontext='buttontext button',
                      buttonadd='icon plus icon-plus glyphicon glyphicon-plus',
                      buttonback='icon arrowleft icon-arrow-left glyphicon glyphicon-arrow-left',
                      buttonexport='icon downarrow icon-download glyphicon glyphicon-download',
                      buttondelete='icon trash icon-trash glyphicon glyphicon-trash',
                      buttonedit='icon pen icon-pencil glyphicon glyphicon-pencil',
                      buttontable='icon rightarrow icon-arrow-right glyphicon glyphicon-arrow-right',
                      buttonview='icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in'
                      )
        elif not isinstance(ui, dict):
            raise RuntimeError('SQLFORM.grid ui argument must be a dictionary')

        db = query._db
        T = current.T
        request = current.request
        session = current.session
        response = current.response
        logged = session.auth and session.auth.user
        wenabled = (not user_signature or logged) and not groupby
        create = wenabled and create
        editable = wenabled and editable
        deletable = wenabled and deletable
        details = details and not groupby
        rows = None

        # see issue 1980. Basically we can have keywords in get_vars
        # (i.e. when the search term is propagated through page=2&keywords=abc)
        # but if there is keywords in post_vars (i.e. POSTing a search request)
        # the one in get_vars should be replaced by the new one
        keywords = ''
        if 'keywords' in request.post_vars:
            keywords = request.post_vars.keywords
        elif 'keywords' in request.get_vars:
            keywords = request.get_vars.keywords

        def fetch_count(dbset):
            ##FIXME for google:datastore cache_count is ignored
            ## if it's not an integer
            if cache_count is None or isinstance(cache_count, tuple):
                if groupby:
                    c = 'count(*) AS count_all'
                    nrows = db.executesql(
                        'select count(*) from (%s) _tmp;' %
                        dbset._select(c, left=left, cacheable=True,
                                      groupby=groupby,
                                      cache=cache_count)[:-1])[0][0]
                elif left:
                    c = 'count(*)'
                    nrows = dbset.select(c, left=left, cacheable=True, cache=cache_count).first()[c]
                elif dbset._db._adapter.dbengine == 'google:datastore':
                    # if we don't set a limit, this can timeout for a large table
                    nrows = dbset.db._adapter.count(dbset.query, limit=1000)
                else:
                    nrows = dbset.count(cache=cache_count)
            elif isinstance(cache_count, integer_types):
                nrows = cache_count
            elif callable(cache_count):
                nrows = cache_count(dbset, request.vars)
            else:
                nrows = 0
            return nrows

        def fix_orderby(orderby):
            if not auto_pagination:
                return orderby
            # enforce always an ORDER clause to avoid
            # pagination errors. field_id is needed anyhow,
            # is unique and usually indexed. See issue #679
            if not orderby:
                orderby = field_id
            elif isinstance(orderby, list):
                orderby = reduce(lambda a, b: a | b, orderby)
            elif isinstance(orderby, Field) and orderby is not field_id:
                # here we're with an ASC order on a field stored as orderby
                orderby = orderby | field_id
            elif (isinstance(orderby, Expression) and
                  orderby.first and orderby.first is not field_id):
                # here we're with a DESC order on a field stored as orderby.first
                orderby = orderby | field_id
            return orderby

        def url(**b):
            b['args'] = args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        def url2(**b):
            b['args'] = request.args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        referrer = session.get('_web2py_grid_referrer_' + formname, url())
        # if not user_signature every action is accessible
        # else forbid access unless
        # - url is based url
        # - url has valid signature (vars are not signed, only path_info)
        # = url does not contain 'create','delete','form' (readonly)
        if user_signature:
            if not ('/'.join(map(str, args)) == '/'.join(map(str, request.args)) or
                    URL.verify(request, user_signature=user_signature, hash_vars=False) or
                    (request.args(len(args)) == 'view' and not logged)):
                session.flash = T('not authorized')
                redirect(referrer)

        def gridbutton(buttonclass='buttonadd', buttontext=T('Add'),
                       buttonurl=url(args=[]), callback=None,
                       delete=None, trap=True, noconfirm=None, title=None):
            if showbuttontext:
                return A(SPAN(_class=ui.get(buttonclass)), CAT(' '),
                         SPAN(T(buttontext), _title=title or T(buttontext),
                              _class=ui.get('buttontext')),
                         _href=buttonurl,
                         callback=callback,
                         delete=delete,
                         noconfirm=noconfirm,
                         _class=ui.get('button'),
                         cid=request.cid)
            else:
                return A(SPAN(_class=ui.get(buttonclass)),
                         _href=buttonurl,
                         callback=callback,
                         delete=delete,
                         noconfirm=noconfirm,
                         _title=title or T(buttontext),
                         _class=ui.get('button'),
                         cid=request.cid)

        dbset = db(query, ignore_common_filters=ignore_common_filters)
        tablenames = db._adapter.tables(dbset.query)
        if left is not None:
            if not isinstance(left, (list, tuple)):
                left = [left]
            for join in left:
                tablenames = merge_tablemaps(tablenames, db._adapter.tables(join))
        tables = [db[tablename] for tablename in tablenames]
        if fields:
            # add missing tablename to virtual fields
            for table in tables:
                for k, f in iteritems(table):
                    if isinstance(f, Field.Virtual):
                        f.tablename = table._tablename
            columns = [f for f in fields if f.tablename in tablenames and f.listable]
        else:
            fields = []
            columns = []
            filter1 = lambda f: isinstance(f, Field) and (f.type != 'blob' or showblobs)
            filter2 = lambda f: isinstance(f, Field) and f.readable and f.listable
            for table in tables:
                fields += filter(filter1, table)
                columns += filter(filter2, table)
                for k, f in iteritems(table):
                    if not k.startswith('_'):
                        if isinstance(f, Field.Virtual) and f.readable:
                            f.tablename = table._tablename
                            fields.append(f)
                            columns.append(f)
        if not field_id:
            if groupby is None:
                field_id = tables[0]._id
            elif groupby and isinstance(groupby, Field):
                # take the field passed as groupby
                field_id = groupby
            elif groupby and isinstance(groupby, Expression):
                # take the first groupby field
                field_id = groupby.first
                while not (isinstance(field_id, Field)):
                    # Navigate to the first Field of the expression
                    field_id = field_id.first
        table = field_id.table
        tablename = table._tablename
        if not any(str(f) == str(field_id) for f in fields):
            fields = [f for f in fields] + [field_id]
        if upload == '<default>':
            upload = lambda filename: url(args=['download', filename])
            if request.args(-2) == 'download':
                stream = response.download(request, db)
                raise HTTP(200, stream, **response.headers)

        def buttons(edit=False, view=False, record=None):
            buttons = DIV(gridbutton('buttonback', 'Back', referrer),
                          _class='form_header row_buttons %(header)s %(cornertop)s' % ui)
            if edit and (not callable(edit) or edit(record)):
                args = ['form', table._tablename, request.args[-1]]
                buttons.append(gridbutton('buttonedit', 'Edit',
                                          url(args=args)))
            if view:
                args = ['view', table._tablename, request.args[-1]]
                buttons.append(gridbutton('buttonview', 'View',
                                          url(args=args)))
            if record and links:
                for link in links:
                    if isinstance(link, dict):
                        buttons.append(link['body'](record))
                    elif link(record):
                        buttons.append(link(record))
            return buttons

        def linsert(lst, i, x):
            """Internal use only: inserts x list into lst at i pos::

                a = [1, 2]
                linsert(a, 1, [0, 3])
                a = [1, 0, 3, 2]
            """
            lst[i:i] = x

        formfooter = DIV(
            _class='form_footer row_buttons %(header)s %(cornerbottom)s' % ui)

        create_form = update_form = view_form = search_form = None

        if create and request.args(-2) == 'new':
            table = db[request.args[-1]]
            sqlformargs = dict(ignore_rw=ignore_rw, formstyle=formstyle,
                               _class='web2py_form')
            sqlformargs.update(formargs)
            sqlformargs.update(createargs)
            create_form = SQLFORM(table, **sqlformargs)
            create_form.process(formname=formname,
                                next=referrer,
                                onvalidation=onvalidation,
                                onfailure=onfailure,
                                onsuccess=oncreate)
            res = DIV(buttons(), create_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif details and request.args(-3) == 'view':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(referrer)
            if represent_none is not None:
                for field in record.iterkeys():
                    if record[field] is None:
                        record[field] = represent_none
            sqlformargs = dict(upload=upload, ignore_rw=ignore_rw,
                               formstyle=formstyle, readonly=True,
                               _class='web2py_form')
            sqlformargs.update(formargs)
            sqlformargs.update(viewargs)
            view_form = SQLFORM(table, record, **sqlformargs)
            res = DIV(buttons(edit=editable, record=record), view_form,
                      formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif editable and request.args(-3) == 'form':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            deletable_ = deletable(record) \
                if callable(deletable) else deletable
            sqlformargs = dict(upload=upload, ignore_rw=ignore_rw,
                               formstyle=formstyle, deletable=deletable_,
                               _class='web2py_form',
                               submit_button=T('Submit'),
                               delete_label=T('Check to delete'))
            sqlformargs.update(formargs)
            sqlformargs.update(editargs)
            update_form = SQLFORM(table, record, **sqlformargs)
            update_form.process(
                formname=formname,
                onvalidation=onvalidation,
                onfailure=onfailure,
                onsuccess=onupdate,
                next=referrer)
            res = DIV(buttons(view=details, record=record),
                      update_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif deletable and request.args(-3) == 'delete':
            table = db[request.args[-2]]
            if not callable(deletable):
                if ondelete:
                    ondelete(table, request.args[-1])
                db(table[table._id.name] == request.args[-1]).delete()
            else:
                record = table(request.args[-1]) or redirect(URL('error'))
                if deletable(record):
                    if ondelete:
                        ondelete(table, request.args[-1])
                    db(table[table._id.name] == request.args[-1]).delete()
            if request.ajax:
                # this means javascript is enabled, so we don't need to do
                # a redirect
                if not client_side_delete:
                    # if it's an ajax request and we don't need to reload the
                    # entire page, let's just inform that there have been no
                    # exceptions and don't regenerate the grid
                    raise HTTP(200)
                else:
                    # if it's requested that the grid gets reloaded on delete
                    # on ajax, the redirect should be on the original location
                    newloc = request.env.http_web2py_component_location
                    redirect(newloc, client_side=client_side_delete)
            else:
                # we need to do a redirect because javascript is not enabled
                redirect(referrer, client_side=client_side_delete)

        exportManager = dict(
            csv_with_hidden_cols=(ExporterCSV_hidden, 'CSV (hidden cols)', T(
                'Comma-separated export including columns not shown; fields from other tables are exported as raw values for faster export')),
            csv=(ExporterCSV, 'CSV', T(
                'Comma-separated export of visible columns. Fields from other tables are exported as they appear on-screen but this may be slow for many rows')),
            xml=(ExporterXML, 'XML', T('XML export of columns shown')),
            html=(ExporterHTML, 'HTML', T('HTML export of visible columns')),
            json=(ExporterJSON, 'JSON', T('JSON export of visible columns')),
            tsv_with_hidden_cols=(ExporterTSV_hidden, 'TSV (Spreadsheets, hidden cols)', T(
                'Spreadsheet-optimised export of tab-separated content including hidden columns. May be slow')),
            tsv=(ExporterTSV, 'TSV (Spreadsheets)',
                 T('Spreadsheet-optimised export of tab-separated content, visible columns only. May be slow.')))
        if exportclasses is not None:
            """
            remember: allow to set exportclasses=dict(csv=False, csv_with_hidden_cols=False) to disable the csv format
            """
            exportManager.update(exportclasses)

        export_type = request.vars._export_type
        if export_type:
            order = request.vars.order or ''
            if sortable:
                if order and not order == 'None':
                    otablename, ofieldname = order.split('~')[-1].split('.', 1)
                    sort_field = db[otablename][ofieldname]
                    exception = sort_field.type in ('date', 'datetime', 'time')
                    if exception:
                        orderby = (order[:1] == '~' and sort_field) or ~sort_field
                    else:
                        orderby = (order[:1] == '~' and ~sort_field) or sort_field

            orderby = fix_orderby(orderby)

            expcolumns = [str(f) for f in columns]
            selectable_columns = [str(f) for f in columns if not isinstance(f, Field.Virtual)]
            if export_type.endswith('with_hidden_cols'):
                # expcolumns = [] start with the visible columns, which
                # includes visible virtual fields
                selectable_columns = []
                # like expcolumns but excluding virtual
                for table in tables:
                    for field in table:
                        if field.readable and field.tablename in tablenames:
                            if not str(field) in expcolumns:
                                expcolumns.append(str(field))
                            if not (isinstance(field, Field.Virtual)):
                                selectable_columns.append(str(field))
                    # look for virtual fields not displayed (and virtual method
                    # fields to be added here?)
                    for (field_name, field) in iteritems(table):
                        if isinstance(field, Field.Virtual) and not str(field) in expcolumns:
                            expcolumns.append(str(field))


            if db._adapter.dbengine == 'mysql':
                expcolumns = ['%s' % '.'.join(f.split('.')) for f in expcolumns]
            else:
                expcolumns = ['"%s"' % '"."'.join(f.split('.')) for f in expcolumns]
            if export_type in exportManager and exportManager[export_type]:
                if keywords:
                    try:
                        # the query should be constructed using searchable
                        # fields but not virtual fields
                        is_searchable = lambda f: f.readable and not isinstance(f, Field.Virtual) and f.searchable
                        sfields = reduce(lambda a, b: a + b, [filter(is_searchable, t) for t in tables])
                        # use custom_query using searchable
                        if callable(searchable):
                            dbset = dbset(searchable(sfields, keywords))
                        else:
                            dbset = dbset(SQLFORM.build_query(
                                [f for f in sfields], keywords))
                        rows = dbset.select(left=left, orderby=orderby,
                                            cacheable=True, *expcolumns)
                    except Exception as e:
                        response.flash = T('Internal Error')
                        rows = []
                else:
                    rows = dbset.select(left=left, orderby=orderby,
                                        cacheable=True, *expcolumns)

                value = exportManager[export_type]
                clazz = value[0] if hasattr(value, '__getitem__') else value
                # expcolumns is all cols to be exported including virtual fields
                try:
                    exporter_args = value[3]
                except:
                    exporter_args = {}
                rows.colnames = expcolumns
                oExp = clazz(rows, **exporter_args)
                export_filename = \
                    request.vars.get('_export_filename') or 'rows'
                filename = '.'.join((export_filename, oExp.file_ext))
                response.headers['Content-Type'] = oExp.content_type
                response.headers['Content-Disposition'] = \
                    'attachment;filename=' + filename + ';'
                raise HTTP(200, oExp.export(), **response.headers)

        elif request.vars.records and not isinstance(
                request.vars.records, list):
            request.vars.records = [request.vars.records]
        elif not request.vars.records:
            request.vars.records = []

        session['_web2py_grid_referrer_' + formname] = url2(vars=request.get_vars)
        console = DIV(_class='web2py_console %(header)s %(cornertop)s' % ui)
        error = None
        if create:
            add = gridbutton(
                buttonclass='buttonadd',
                buttontext=T('Add Record'),
                title=T("Add record to database"),
                buttonurl=url(args=['new', tablename]))
            if not searchable:
                console.append(add)
        else:
            add = ''

        if searchable:
            sfields = reduce(lambda a, b: a + b,
                             [[f for f in t if f.readable] for t in tables])
            if isinstance(search_widget, dict):
                search_widget = search_widget[tablename]
            if search_widget == 'default':
                prefix = formname == 'web2py_grid' and 'w2p' or 'w2p_%s' % formname
                search_menu = Grid.search_menu(sfields, prefix=prefix)
                spanel_id = '%s_query_fields' % prefix
                sfields_id = '%s_query_panel' % prefix
                skeywords_id = '%s_keywords' % prefix
                # hidden fields to presever keywords in url after the submit
                hidden_fields = [INPUT(_type='hidden', _value=v, _name=k) for k, v in request.get_vars.items() if
                                 k not in ['keywords', 'page']]
                search_widget = lambda sfield, url: CAT(FORM(
                    INPUT(_name='keywords', _value=keywords,
                          _id=skeywords_id, _class='form-control',
                          _onfocus="jQuery('#%s').change();jQuery('#%s').slideDown();" % (
                          spanel_id, sfields_id) if advanced_search else ''
                          ),
                    INPUT(_type='submit', _value=T('Search'), _class="btn btn-default btn-secondary"),
                    INPUT(_type='submit', _value=T('Clear'), _class="btn btn-default btn-secondary",
                          _onclick="jQuery('#%s').val('');" % skeywords_id),
                    *hidden_fields,
                    _method="GET", _action=url), search_menu)
            # TODO vars from the url should be removed, they are not used by the submit
            form = search_widget and search_widget(sfields, url()) or ''
            console.append(add)
            console.append(form)
            try:
                if callable(searchable):
                    subquery = searchable(sfields, keywords)
                else:
                    subquery = SQLFORM.build_query(sfields, keywords)
            except RuntimeError:
                subquery = None
                error = T('Invalid query')
        else:
            subquery = None

        if subquery:
            dbset = dbset(subquery)
        try:
            nrows = fetch_count(dbset)
        except:
            nrows = 0
            error = T('Unsupported query')

        order = request.vars.order or ''
        if sortable:
            if order and not order == 'None':
                otablename, ofieldname = order.split('~')[-1].split('.', 1)
                sort_field = db[otablename][ofieldname]
                exception = sort_field.type in ('date', 'datetime', 'time')
                if exception:
                    orderby = (order[:1] == '~' and sort_field) or ~sort_field
                else:
                    orderby = (order[:1] == '~' and ~sort_field) or sort_field

        headcols = []
        if selectable:
            headcols.append(TH(_class=ui.get('default')))

        ordermatch, marker = orderby, ''
        if orderby:
            # if orderby is a single column, remember to put the marker
            if isinstance(orderby, Expression):
                if orderby.first and not orderby.second:
                    ordermatch, marker = orderby.first, '~'
        ordermatch = marker + str(ordermatch)
        for field in columns:
            if not field.readable:
                continue
            key = str(field)
            header = headers.get(str(field), field.label or key)
            if sortable and not isinstance(field, Field.Virtual):
                marker = ''
                if order:
                    if key == order:
                        key, marker = '~' + order, sorter_icons[0]
                    elif key == order[1:]:
                        marker = sorter_icons[1]
                else:
                    if key == ordermatch:
                        key, marker = '~' + ordermatch, sorter_icons[0]
                    elif key == ordermatch[1:]:
                        marker = sorter_icons[1]
                header = A(header, marker, _href=url(vars=dict(
                    keywords=keywords,
                    order=key)), cid=request.cid)
            headcols.append(TH(header, _class=ui.get('default')))

        toadd = []
        left_cols = 0
        right_cols = 0
        if links and links_in_grid:
            for link in links:
                if isinstance(link, dict):
                    toadd.append(TH(link['header'], _class=ui.get('default')))
            if links_placement in ['right', 'both']:
                headcols.extend(toadd)
                right_cols += len(toadd)
            if links_placement in ['left', 'both']:
                linsert(headcols, 0, toadd)
                left_cols += len(toadd)

        # Include extra column for buttons if needed.
        include_buttons_column = (
                details or editable or deletable or
                (links and links_in_grid and
                 not all([isinstance(link, dict) for link in links])))
        if include_buttons_column:
            header_element = TH(_class=ui.get('default', ''))
            if buttons_placement in ['right', 'both']:
                headcols.append(header_element)
                right_cols += 1
            if buttons_placement in ['left', 'both']:
                headcols.insert(0, header_element)
                left_cols += 1

        head = TR(*headcols, **dict(_class=ui.get('header')))

        cursor = True
        # figure out what page we are on to setup the limitby
        if paginate and dbset._db._adapter.dbengine == 'google:datastore' and use_cursor:
            cursor = request.vars.cursor or True
            limitby = (0, paginate)
            page = safe_int(request.vars.page or 1, 1) - 1
        elif paginate and paginate < nrows:
            page = safe_int(request.vars.page or 1, 1) - 1
            limitby = (paginate * page, paginate * (page + 1))
        else:
            limitby = None

        orderby = fix_orderby(orderby)

        try:
            table_fields = [field for field in fields
                            if (field.tablename in tablenames and
                                not (isinstance(field, Field.Virtual)))]
            if dbset._db._adapter.dbengine == 'google:datastore' and use_cursor:
                rows = dbset.select(left=left, orderby=orderby,
                                    groupby=groupby, limitby=limitby,
                                    reusecursor=cursor,
                                    cacheable=True, *table_fields)
                next_cursor = dbset._db.get('_lastcursor', None)
            else:
                rows = dbset.select(left=left, orderby=orderby,
                                    groupby=groupby, limitby=limitby,
                                    cacheable=True, *table_fields)
                next_cursor = None
        except SyntaxError:
            rows = None
            next_cursor = None
            error = T("Query Not Supported")
        except Exception as e:
            rows = None
            next_cursor = None
            error = T("Query Not Supported: %s") % e

        message = error
        if not message and nrows:
            if dbset._db._adapter.dbengine == 'google:datastore' and nrows >= 1000:
                message = T('at least %(nrows)s records found') % dict(nrows=nrows)
            else:
                message = T('%(nrows)s records found') % dict(nrows=nrows)
        console.append(DIV(message or '', _class='web2py_counter'))

        paginator = UL()
        if paginate and dbset._db._adapter.dbengine == 'google:datastore' and use_cursor:
            # this means we may have a large table with an unknown number of rows.
            page = safe_int(request.vars.page or 1, 1) - 1
            paginator.append(LI('page %s' % (page + 1)))
            if next_cursor:
                d = dict(page=page + 2, cursor=next_cursor)
                if order:
                    d['order'] = order
                # see issue 1980, also at the top of the definition
                # if keyworkds is in request.vars, we don't need to
                # copy over the keywords parameter in the links for pagination
                if 'keywords' in request.vars and not keywords:
                    d['keywords'] = ''
                elif keywords:
                    d['keywords'] = keywords
                paginator.append(LI(
                    A('next', _href=url(vars=d), cid=request.cid)))
        elif paginate and paginate < nrows:
            npages, reminder = divmod(nrows, paginate)
            if reminder:
                npages += 1
            page = safe_int(request.vars.page or 1, 1) - 1

            def self_link(name, p):
                d = dict(page=p + 1)
                if order:
                    d['order'] = order
                # see issue 1980, also at the top of the definition
                # if keyworkds is in request.vars, we don't need to
                # copy over the keywords parameter in the links for pagination
                if 'keywords' in request.vars and not keywords:
                    d['keywords'] = ''
                elif keywords:
                    d['keywords'] = keywords
                return A(name, _href=url(vars=d), cid=request.cid)

            NPAGES = 5  # window is 2*NPAGES
            if page > NPAGES + 1:
                paginator.append(LI(self_link('<<', 0)))
            if page > NPAGES:
                paginator.append(LI(self_link('<', page - 1)))
            pages = range(max(0, page - NPAGES), min(page + NPAGES, npages))
            for p in pages:
                if p == page:
                    paginator.append(LI(A(p + 1, _onclick='return false'),
                                        _class='current'))
                else:
                    paginator.append(LI(self_link(p + 1, p)))
            if page < npages - NPAGES:
                paginator.append(LI(self_link('>', page + 1)))
            if page < npages - NPAGES - 1:
                paginator.append(LI(self_link('>>', npages - 1)))
        else:
            limitby = None

        if rows:
            cols = [COL(_id=str(c).replace('.', '-'),
                        data={'column': left_cols + i + 1})
                    for i, c in enumerate(columns)]
            cols = [COL(data={'column': i + 1}) for i in range(left_cols)] + \
                   cols + \
                   [COL(data={'column': left_cols + len(cols) + i + 1})
                    for i in range(right_cols)]
            htmltable = TABLE(COLGROUP(*cols), THEAD(head), _class=table_class)
            tbody = TBODY()
            numrec = 0
            repr_cache = CacheRepresenter()
            for row in rows:
                trcols = []
                id = row[field_id]
                if selectable:
                    trcols.append(
                        INPUT(_type="checkbox", _name="records", _value=id,
                              value=request.vars.records))
                for field in columns:
                    if not field.readable:
                        continue
                    elif field.type == 'blob' and not showblobs:
                        continue
                    if isinstance(field, Field.Virtual) and field.tablename in row:
                        try:
                            # fast path, works for joins
                            value = row[field.tablename][field.name]
                        except KeyError:
                            value = dbset.db[field.tablename][row[field.tablename][field_id]][field.name]
                    else:
                        value = row[str(field)]
                    maxlength = maxtextlengths.get(str(field), maxtextlength)
                    if field.represent:
                        if field.type.startswith('reference'):
                            nvalue = repr_cache(field, value, row)
                        else:
                            try:
                                nvalue = field.represent(value, row)
                            except KeyError:
                                try:
                                    nvalue = field.represent(value, row[field.tablename])
                                except KeyError:
                                    nvalue = None
                        value = nvalue
                    elif field.type == 'boolean':
                        value = INPUT(_type="checkbox", _checked=value,
                                      _disabled=True)
                    elif field.type == 'upload':
                        if value:
                            if callable(upload):
                                value = A(
                                    T('file'), _href=upload(value))
                            elif upload:
                                value = A(T('file'),
                                          _href='%s/%s' % (upload, value))
                        else:
                            value = ''
                    elif isinstance(field.type, SQLCustomType) and callable(field.type.represent):
                        # SQLCustomType has a represent, use it
                        value = field.type.represent(value, row)
                    if isinstance(value, str):
                        value = truncate_string(value, maxlength)
                    elif not isinstance(value, XmlComponent):
                        value = field.formatter(value)
                    if value is None:
                        value = represent_none
                    trcols.append(TD(value))
                row_buttons = TD(_class='row_buttons', _nowrap=True)
                if links and links_in_grid:
                    toadd = []
                    for link in links:
                        if isinstance(link, dict):
                            toadd.append(TD(link['body'](row)))
                        else:
                            if link(row):
                                row_buttons.append(link(row))
                    if links_placement in ['right', 'both']:
                        trcols.extend(toadd)
                    if links_placement in ['left', 'both']:
                        linsert(trcols, 0, toadd)

                if include_buttons_column:
                    if details and (not callable(details) or details(row)):
                        row_buttons.append(gridbutton(
                            'buttonview', 'View',
                            url(args=['view', tablename, id])))
                    if editable and (not callable(editable) or editable(row)):
                        row_buttons.append(gridbutton(
                            'buttonedit', 'Edit',
                            url(args=['form', tablename, id])))
                    if deletable and (not callable(deletable) or deletable(row)):
                        row_buttons.append(gridbutton(
                            'buttondelete', 'Delete',
                            url(args=['delete', tablename, id]),
                            callback=url(args=['delete', tablename, id]),
                            noconfirm=noconfirm,
                            delete='tr'))
                    if buttons_placement in ['right', 'both']:
                        trcols.append(row_buttons)
                    if buttons_placement in ['left', 'both']:
                        trcols.insert(0, row_buttons)
                # if numrec % 2 == 1:
                #     classtr = 'w2p_even even'
                # else:
                #     classtr = 'w2p_odd odd'
                # numrec += 1
                if id:
                    rid = id
                    if callable(rid):  # can this ever be callable?
                        rid = rid(row)
                    tr = TR(*trcols, **dict(
                        _id=rid,
                        # _class='%s %s' % (classtr, 'with_id')))
                        _class='with_id'))
                else:
                    tr = TR(*trcols)
                tbody.append(tr)
            htmltable.append(tbody)
            htmltable = DIV(
                htmltable, _class='web2py_htmltable',
                _style='width:100%;overflow-x:auto;-ms-overflow-x:scroll')
            if selectable:
                if not callable(selectable):
                    # now expect that selectable and related parameters are
                    # iterator (list, tuple, etc)
                    inputs = []
                    for i, submit_info in enumerate(selectable):
                        submit_text = submit_info[0]
                        submit_class = submit_info[2] if len(submit_info) > 2 else ''

                        input_ctrl = INPUT(_type="submit", _name='submit_%d' % i, _value=T(submit_text))
                        input_ctrl.add_class(submit_class)
                        inputs.append(input_ctrl)
                else:
                    inputs = [INPUT(_type="submit", _value=T(selectable_submit_button))]

                if formstyle == 'bootstrap':
                    # add space between buttons
                    htmltable = FORM(htmltable, DIV(_class='form-actions', *inputs))
                elif 'bootstrap' in formstyle:  # Same for bootstrap 3 & 4
                    htmltable = FORM(htmltable, DIV(_class='form-group web2py_table_selectable_actions', *inputs))
                else:
                    htmltable = FORM(htmltable, *inputs)

                if htmltable.process(formname=formname).accepted:
                    htmltable.vars.records = htmltable.vars.records or []
                    htmltable.vars.records = htmltable.vars.records if isinstance(htmltable.vars.records, list) else [
                        htmltable.vars.records]
                    records = [int(r) for r in htmltable.vars.records]
                    if not callable(selectable):
                        for i, submit_info in enumerate(selectable):
                            submit_callback = submit_info[1]
                            if htmltable.vars.get('submit_%d' % i, False):
                                submit_callback(records)
                                break
                    else:
                        selectable(records)
                    redirect(referrer)
        else:
            htmltable = DIV(T('No records found'))

        if csv and nrows:
            export_links = []
            for k, v in sorted(exportManager.items()):
                if not v:
                    continue
                if hasattr(v, "__getitem__"):
                    label = v[1]
                    title = v[2] if len(v) > 2 else label
                else:
                    label = title = k
                link = url2(vars=dict(
                    order=request.vars.order or '',
                    _export_type=k,
                    keywords=keywords or ''))
                export_links.append(A(T(label), _href=link, _title=title, _class='btn btn-default btn-secondary'))
            export_menu = \
                DIV(T('Export:'), _class="w2p_export_menu", *export_links)
        else:
            export_menu = None

        res = DIV(console, DIV(htmltable, _class="web2py_table"),
                  _class='%s %s' % (_class, ui.get('widget')))
        if paginator.components:
            res.append(
                DIV(paginator,
                    _class="web2py_paginator %(header)s %(cornerbottom)s" % ui))
        if export_menu:
            res.append(export_menu)
        res.create_form = create_form
        res.update_form = update_form
        res.view_form = view_form
        res.search_form = search_form
        res.rows = rows
        res.dbset = dbset
        return res