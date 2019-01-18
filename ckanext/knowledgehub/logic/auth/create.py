import ckan.plugins.toolkit as toolkit
import ckan.authz as authz
import ckan.logic as logic


def theme_create(context, data_dict):
    '''
        Authorization check for creating theme
    '''
    # sysadmins only
    return {'success': False}


def sub_theme_create(context, data_dict):
    user = context.get('user')
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized

    return {'success': True}


@toolkit.auth_disallow_anonymous_access
def research_question_create(context, data_dict):
    return {'success': True}