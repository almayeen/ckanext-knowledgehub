from ckan.model import ResourceView, resource_view_table
from ckan.model.meta import mapper
from ckan.logic import get_action

from sqlalchemy import Column, types

from ckanext.knowledgehub.lib.solr import (
    Indexed,
    mapped,
    unprefixed,
    DontIndexException
)
from ckanext.knowledgehub.model.research_question import ResearchQuestion
import json
from logging import getLogger


log = getLogger(__name__)


class Visualization(ResourceView, Indexed):

    indexed = [
        mapped('id', 'entity_id'),
        'resource_id',
        'title',
        'description',
        'view_type',
        'research_questions',
        'package_id',
        'keywords',
        mapped('tags', 'tags'),
        mapped('organizations', 'organizations'),
        mapped('groups', 'groups'),
        unprefixed('idx_keywords'),
        unprefixed('idx_tags'),
        unprefixed('idx_research_questions'),
        unprefixed('permission_labels'),
    ]

    doctype = 'visualization'

    @staticmethod
    def before_index(data):
        # Index only charts
        if data.get('view_type') not in ['chart', 'map']:
            raise DontIndexException(data.get('id'))

        permission_labels = []

        resource_view = get_action('resource_view_show')(
            {'ignore_auth': True},
            {'id': data['id']})

        data['package_id'] = resource_view['package_id']
        package = get_action('package_show')(
            {'ignore_auth': True},
            {'id': data['package_id'], 'include_tracking': True})
        if package:
            data['organizations'] = (package.get('organization',
                                                 {}) or {}).get('name')
            organization_id = (package.get('organization', {}) or {}).get('id')
            if organization_id:
                permission_labels.append('member-%s' % organization_id)

            data['groups'] = []
            for g in package.get('groups', []):
                data['groups'].append(g['name'])
                permission_labels.append('member-%s' % g['id'])

        if data.get('_sa_instance_state'):
            del data['_sa_instance_state']
        if data.get('description') is not None:
            return data

        def _get_description(data_dict):
            if not data_dict.get('__extras'):
                return None
            extras = data_dict['__extras']
            if data['view_type'] == 'chart':
                return extras.get('chart_description', '')
            elif data['view_type'] == 'table':
                return extras.get('table_description', '')
            elif data['view_type'] == 'map':
                return extras.get('map_description', '')
            else:
                # guess the description
                for prop, value in extras.items():
                    if prop == 'description' or prop.endswith('_description'):
                        return value

        if not data.get('__extras'):
            if resource_view.get('description') is not None:
                data['description'] = resource_view['description']
            else:
                data['description'] = _get_description(resource_view)
        else:
            data['description'] = _get_description(data)

        # get research questions
        rq_ids = set()
        if data.get('config'):
            conf = data.get('config')
            if conf.get('__extras'):
                ext = conf.get('__extras')
                if ext.get('research_questions'):
                    data_rq = json.dumps(ext.get('research_questions'))
                    data['research_questions'] = data_rq
                    if isinstance(data_rq, dict):
                        rq_ids.add(data_rq.get('id'))
                    elif isinstance(data_rq, str):
                        rq_ids.add(data_rq)
        else:
            if data.get('__extras'):
                ext = data.get('__extras')
                if ext.get('research_questions'):
                    data_rq = json.dumps(ext.get('research_questions'))
                    data['research_questions'] = data_rq
                    if isinstance(data_rq, dict):
                        rq_ids.add(data_rq.get('id'))
                    elif isinstance(data_rq, str):
                        rq_ids.add(data_rq)

        if rq_ids:
            rq_ids_list = list(rq_ids)
            string_ids = ','.join(rq_ids_list)
            clean = string_ids.replace('"', "").replace(']',"").replace("[","")
            clean_list = clean.split(',')
        
            data['idx_research_questions'] = []

            for rq_title in clean_list:
                try:
                    rq_title = rq_title.strip(" ")
                    rq = ResearchQuestion.get_by_id_name_or_title(rq_title)
                    if rq:
                        data['idx_research_questions'].append(rq.id)
                except Exception as e:
                    log.warning('Failed to fetch research question %s. '
                                'Error: %s',
                                rq_title,
                                str(e))
                    log.exception(e)

        keywords = set()
        if data.get('tags'):
            data['tags'] = data.get('tags').split(',')
            data['idx_tags'] = data['tags']
            for tag in data['tags']:
                tag_obj = get_action('tag_show')(
                    {'ignore_auth': True},
                    {'id': tag}
                )
                if tag_obj.get('keyword_id'):
                    keyword_obj = get_action('keyword_show')(
                        {'ignore_auth': True},
                        {'id': tag_obj.get('keyword_id')}
                    )
                    keywords.add(keyword_obj.get('name'))

        if keywords:
            data['keywords'] = ','.join(keywords)
            data['idx_keywords'] = list(keywords)

        if permission_labels:
            data['permission_labels'] = permission_labels

        return data


mapper(Visualization, resource_view_table)


def column_exists_in_db(column_name, table_name, engine):
    for result in engine.execute('select column_name '
                                 'from information_schema.columns '
                                 'where table_name=\'%s\'' % table_name):
        column = result[0]
        if column == column_name:
            return True
    return False


def extend_resource_view_table():
    from ckan import model
    engine = model.meta.engine

    resource_view_table.append_column(Column(
        'tags',
        types.UnicodeText,
    ))

    from sqlalchemy.orm import configure_mappers

    # Hack to update the mapper for the class ResourceView
    # that was already mapped.
    delattr(ResourceView, '_sa_class_manager')
    # Remap the ResourceView class again
    mapper(ResourceView, resource_view_table)

    if column_exists_in_db('tags', 'resource_view', engine):
        return

    # Add the column in DB
    engine.execute('alter table resource_view '
                   'add column tags character varying(100)')


def setup():
    extend_resource_view_table()
