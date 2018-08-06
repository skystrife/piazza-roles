from celery.result import AsyncResult
from datetime import datetime, timedelta
from enum import IntEnum, auto
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import mdmm_sampler

db = SQLAlchemy()

network_user = db.Table(
    'network_user',
    db.Column(
        'network_id',
        db.Integer,
        db.ForeignKey('network.id'),
        primary_key=True),
    db.Column(
        'user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True))


class Network(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nid = db.Column(db.String(20), index=True, unique=True, nullable=False)
    number = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    term = db.Column(db.String(120), nullable=False)
    users = db.relationship(
        'User',
        secondary=network_user,
        lazy='subquery',
        backref=db.backref('networks', lazy=True))
    crawl = db.relationship(
        'Crawl',
        backref='network',
        cascade='all, delete-orphan',
        uselist=False)

    def __repr(self):
        return "<Network: {}:{} ({} {})>".format(self.id, self.nid,
                                                 self.number, self.term)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User: {}>".format(self.email)


class Crawl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(
        db.Integer, db.ForeignKey('network.id'), nullable=False)
    finished = db.Column(db.Boolean, default=False)
    task_id = db.Column(db.String(120), index=True)
    errors = db.relationship(
        'CrawlError',
        backref=db.backref('crawl', lazy=True),
        cascade='all, delete-orphan')

    def __repr__(self):
        return "<Crawl: {}>".format(self.id)

    def progress(self):
        if self.finished:
            return 100
        try:
            result = AsyncResult(self.task_id)
            if result.state == 'PROGRESS':
                return result.info['progress']
        except:
            pass
        return 0

    def create_actions_from_history(self, parent, post):
        #
        # history is in reverse-chronological order
        #
        for idx, item in enumerate(reversed(post['history'])):
            type_id = ActionType.from_post_history(
                parent, post, item, is_edit=(idx != 0))
            time = datetime.strptime(item['created'], '%Y-%m-%dT%H:%M:%SZ')
            if item['subject'] and len(item['subject']) != 0:
                content = "\n".join([item['subject'], item['content']])
            else:
                content = item['content']
            action = Action(
                crawl_id=self.id,
                uid=item['uid'],
                type_id=int(type_id),
                time=time,
                content=content)
            db.session.add(action)

    def create_actions_from_followup(self, parent, post, child=None):
        #
        # because feedback and followup content types are basically the
        # same, we can re-use this function for both. If child is none,
        # then it is a root "followup", otherwise it is a "feedback"
        # comment.
        #
        if child:
            type_id = ActionType.feedback_action_type(parent, post, child)
        else:
            type_id = ActionType.followup_action_type(parent, post)

        time = datetime.strptime(post['created'], '%Y-%m-%dT%H:%M:%SZ')
        action = Action(
            crawl_id=self.id,
            uid=post['uid'],
            type_id=int(type_id),
            time=time,
            content=post['subject'])
        db.session.add(action)

        if not child:
            for child in post['children']:
                create_actions_from_followup(parent, post, child)

    def create_actions_from_post(self, post):
        #
        # there are two layers:
        # root['children'] == ir, sr, followups
        # followup['children] == feedback
        #
        self.create_actions_from_history(post, post)

        for child in post['children']:
            if child['type'] == 'i_answer' or child['type'] == 's_answer':
                self.create_actions_from_history(post, child)
            else:
                self.create_actions_from_followup(post, child)


class CrawlError(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crawl_id = db.Column(db.Integer, db.ForeignKey('crawl.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return "<CrawlError: {}>".format(self.id)


class ActionType(IntEnum):
    Q_POST_ANON = auto()
    Q_POST_NAME = auto()

    Q_EDIT_MQ_ANON = auto()
    Q_EDIT_OQ_ANON = auto()
    Q_EDIT_MQ_NAME = auto()
    Q_EDIT_OQ_NAME = auto()

    N_POST_ANON = auto()
    N_POST_NAME = auto()

    N_EDIT_MN_ANON = auto()
    N_EDIT_ON_ANON = auto()
    N_EDIT_MN_NAME = auto()
    N_EDIT_ON_NAME = auto()

    POLL_POST_ANON = auto()
    POLL_POST_NAME = auto()

    POLL_EDIT_MP_ANON = auto()
    POLL_EDIT_OP_ANON = auto()
    POLL_EDIT_MP_NAME = auto()
    POLL_EDIT_OP_NAME = auto()

    SR_POST_MQ_ANON = auto()
    SR_POST_OQ_ANON = auto()
    SR_POST_MQ_NAME = auto()
    SR_POST_OQ_NAME = auto()

    SR_EDIT_MA_MQ_ANON = auto()
    SR_EDIT_MA_OQ_ANON = auto()
    SR_EDIT_OA_MQ_ANON = auto()
    SR_EDIT_OA_OQ_ANON = auto()
    SR_EDIT_MA_MQ_NAME = auto()
    SR_EDIT_MA_OQ_NAME = auto()
    SR_EDIT_OA_MQ_NAME = auto()
    SR_EDIT_OA_OQ_NAME = auto()

    IR_POST = auto()

    IR_EDIT_MA = auto()
    IR_EDIT_OA = auto()

    FOLLOWUP_MQ_ANON = auto()
    FOLLOWUP_OQ_ANON = auto()
    FOLLOWUP_MQ_NAME = auto()
    FOLLOWUP_OQ_NAME = auto()

    FEEDBACK_MF_MQ_ANON = auto()
    FEEDBACK_MF_OQ_ANON = auto()
    FEEDBACK_OF_MQ_ANON = auto()
    FEEDBACK_OF_OQ_ANON = auto()
    FEEDBACK_MF_MQ_NAME = auto()
    FEEDBACK_MF_OQ_NAME = auto()
    FEEDBACK_OF_MQ_NAME = auto()
    FEEDBACK_OF_OQ_NAME = auto()

    @classmethod
    def note_history_type(cls, is_edit, my_post, anon):
        if not is_edit:
            return cls.N_POST_ANON if anon else cls.N_POST_NAME
        else:
            if my_post and anon:
                return cls.N_EDIT_MN_ANON
            elif my_post and not anon:
                return cls.N_EDIT_MN_NAME
            elif not my_post and anon:
                return cls.N_EDIT_ON_ANON
            else:
                return cls.N_EDIT_ON_NAME

    @classmethod
    def poll_history_type(cls, is_edit, my_post, anon):
        if not is_edit:
            return cls.POLL_POST_ANON if anon else cls.POLL_POST_NAME
        else:
            if my_post and anon:
                return cls.POLL_EDIT_MP_ANON
            elif my_post and not anon:
                return cls.POLL_EDIT_MP_NAME
            elif not my_post and anon:
                return cls.POLL_EDIT_OP_ANON
            else:
                return cls.POLL_EDIT_OP_NAME

    @classmethod
    def question_history_type(cls, is_edit, my_post, anon):
        if not is_edit:
            return cls.Q_POST_ANON if anon else cls.Q_POST_NAME
        else:
            if my_post and anon:
                return cls.Q_EDIT_MQ_ANON
            elif my_post and not anon:
                return cls.Q_EDIT_MQ_NAME
            elif not my_post and anon:
                return cls.Q_EDIT_OQ_ANON
            else:
                return cls.Q_EDIT_OQ_NAME

    @classmethod
    def sr_history_type(cls, is_edit, my_post, my_parent, anon):
        if not is_edit:
            if my_parent:
                return cls.SR_POST_MQ_ANON if anon else cls.SR_POST_MQ_NAME
            else:
                return cls.SR_POST_OQ_ANON if anon else cls.SR_POST_OQ_NAME
        else:
            mapping = {
                (True, True, True): cls.SR_EDIT_MA_MQ_ANON,
                (True, True, False): cls.SR_EDIT_MA_MQ_NAME,
                (True, False, True): cls.SR_EDIT_MA_OQ_ANON,
                (True, False, False): cls.SR_EDIT_MA_OQ_NAME,
                (False, True, True): cls.SR_EDIT_OA_MQ_ANON,
                (False, True, False): cls.SR_EDIT_OA_MQ_NAME,
                (False, False, True): cls.SR_EDIT_OA_OQ_ANON,
                (False, False, False): cls.SR_EDIT_OA_OQ_NAME
            }
            return mapping[(my_post, my_parent, anon)]

    @classmethod
    def ir_history_type(cls, is_edit, my_post):
        if not is_edit:
            return cls.IR_POST
        else:
            return cls.IR_EDIT_MA if my_post else cls.IR_EDIT_OA

    @classmethod
    def followup_action_type(cls, parent, post):
        print(post)
        anon = ('anon' in post and post['anon'] != 'no')
        uid = post['uid']
        my_parent = (parent['history'][-1]['uid'] == uid)

        if my_parent and anon:
            return cls.FOLLOWUP_MQ_ANON
        elif my_parent and not anon:
            return cls.FOLLOWUP_MQ_NAME
        elif not my_parent and anon:
            return cls.FOLLOWUP_OQ_ANON
        else:
            return cls.FOLLOWUP_OQ_NAME

    @classmethod
    def feedback_action_type(cls, root, parent, post):
        print(post)
        anon = ('anon' in post and post['anon'] != 'no')
        uid = post['uid']
        my_parent = (parent['history'][-1]['uid'] == uid)
        my_root = (root['history'][-1]['uid'] == uid)

        mapping = {
            (True, True, True): cls.FEEDBACK_MF_MQ_ANON,
            (True, True, False): cls.FEEDBACK_MF_MQ_NAME,
            (True, False, True): cls.FEEDBACK_MF_OQ_ANON,
            (True, False, False): cls.FEEDBACK_MF_OQ_NAME,
            (False, True, True): cls.FEEDBACK_OF_MQ_ANON,
            (False, True, False): cls.FEEDBACK_OF_MQ_NAME,
            (False, False, True): cls.FEEDBACK_OF_OQ_ANON,
            (False, False, False): cls.FEEDBACK_OF_OQ_NAME
        }
        return mapping[(my_parent, my_root, anon)]

    @classmethod
    def from_post_history(cls, parent, post, item, is_edit=False):
        anon = ('anon' in item and item['anon'] != 'no')
        uid = item['uid']
        my_parent = (parent['history'][-1]['uid'] == uid)
        my_post = (post['history'][-1]['uid'] == uid)

        if post['type'] == 'note':
            return cls.note_history_type(is_edit, my_post, anon)
        elif post['type'] == 'poll':
            return cls.poll_history_type(is_edit, my_post, anon)
        elif post['type'] == 'question':
            return cls.question_history_type(is_edit, my_post, anon)
        elif post['type'] == 'i_answer':
            return cls.ir_history_type(is_edit, my_post)
        elif post['type'] == 's_answer':
            return cls.sr_history_type(is_edit, my_post, my_parent, anon)
        else:
            raise Exception('invalid post type')

    def description(self):
        name = self.name

        post_prefix = 'a'
        post_type = None
        if name.startswith('Q_'):
            post_type = 'question'
        elif name.startswith('N_'):
            post_type = 'note'
        elif name.startswith('POLL_'):
            post_type = 'poll'
        elif name.startswith('SR_'):
            post_type = 'student answer'
        elif name.startswith('IR_'):
            post_prefix = 'an'
            post_type = 'instructor answer'
        elif name.startswith('FOLLOWUP_'):
            post_type = 'followup'
        else:  #elif name.startswith('FEEDBACK_'):
            post_type = 'followup comment'

        action = "A post"
        if name.find('EDIT') != -1:
            action = "An edit"

        if name.find('_MF_') != -1:
            post_type += ' on their own followup'
        if name.find('_OF_') != -1:
            post_type += ' on someone else\'s followup'

        def adjust_for_ownership(ptype, ownership):
            new_prefix = post_prefix
            new_post_type = post_type
            if post_type.find(ptype) != -1:
                new_prefix = ownership
            else:
                new_post_type += " on {} {}".format(ownership, ptype)

            return (new_prefix, new_post_type)

        if name.find('_MA') != -1:
            post_prefix, post_type = adjust_for_ownership(
                'answer', 'their own')

        if name.find('_OA') != -1:
            post_prefix, post_type = adjust_for_ownership(
                'answer', 'someone else\'s')

        if name.find('_MQ_') != -1:
            post_prefix, post_type = adjust_for_ownership(
                'question', 'their own')

        if name.find('_OQ_') != -1:
            post_prefix, post_type = adjust_for_ownership(
                'question', 'someone else\'s')

        if name.find('_MN_') != -1:
            post_prefix, post_type = adjust_for_ownership('note', 'their own')

        if name.find('_ON_') != -1:
            post_prefix, post_type = adjust_for_ownership(
                'note', 'someone else\'s')

        if name.find('_MP_') != -1:
            post_prefix, post_type = adjust_for_ownership('poll', 'their own')

        if name.find('_OP_') != -1:
            post_prefix, post_type = adjust_for_ownership(
                'poll', 'someone else\'s')

        anonymous = 'anonymously' if name.find(
            'ANON') != -1 else 'non-anonymously'

        return "{} of {} {} {}".format(action, post_prefix, post_type,
                                       anonymous)


class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crawl_id = db.Column(db.Integer, db.ForeignKey('crawl.id'), nullable=False)
    crawl = db.relationship(
        'Crawl',
        backref=db.backref('actions', lazy=True, cascade='all, delete-orphan'))
    uid = db.Column(db.String(120), nullable=False, index=True)
    type_id = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    content = db.deferred(db.Column(db.Text))

    def action_type(self):
        return ActionType(self.type_id)


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crawl_id = db.Column(db.Integer, db.ForeignKey('crawl.id'), nullable=False)
    crawl = db.relationship(
        'Crawl',
        backref=db.backref(
            'analyses', lazy=True, cascade='all, delete-orphan'))
    session_gap = db.Column(db.Float, nullable=False)
    role_count = db.Column(db.Integer, nullable=False)
    max_iterations = db.Column(db.Integer, nullable=False)
    proportion_smoothing = db.Column(db.Float, nullable=False)
    role_smoothing = db.Column(db.Float, nullable=False)
    finished = db.Column(db.Boolean, default=False)
    task_id = db.Column(db.String(120), index=True)

    def progress(self):
        if self.finished:
            return {'sessions': 100, 'sampling': 100}
        try:
            result = AsyncResult(self.task_id)
            if result.state == 'PROGRESS':
                return result.info
        except:
            pass
        return {'sessions': 0, 'sampling': 0}

    def extract_sessions(self, progress_report):
        actions = Action.query.filter_by(crawl_id=self.crawl_id)
        total = actions.count()
        current = 0

        def add_and_report(session, force=False):
            result = current
            if session:
                db.session.add(session)
                result += len(session.actions)
                progress_report(result, total)
            return result

        actions = actions.order_by(Action.uid).order_by(Action.time)
        gap_len = timedelta(hours=self.session_gap)

        uid = None
        session = None
        prev_action = None
        for action in actions:
            # A session "ends" if either the current user is different (we've
            # moved to a different user's action list) or if the gap length
            # between the previous action and this action is more than the
            # analysis' session_gap
            if action.uid != uid or (prev_action and
                                     action.time - prev_action.time > gap_len):
                current = add_and_report(session)
                session = Session(uid=action.uid, analysis_id=self.id)
                uid = action.uid
                prev_action = None

            session.actions.append(action)
            prev_action = action

        current = add_and_report(session)
        db.session.commit()
        return current

    def run_sampler(self, progress_report):
        # Get ordered sessions by time
        sessions = Action.query.join(Action, Session.actions)\
                .filter(Session.analysis_id == self.id)\
                .with_entities(func.min(Action.time).label('start_time'),
                               Session.id, Session.uid)\
                .group_by(Session.id)\
                .order_by(Session.uid)\
                .order_by('start_time').all()

        training_data = []
        user_sessions = []
        current_user = None
        for session in sessions:
            if current_user != session.uid:
                if user_sessions:
                    training_data.append(user_sessions)
                    user_sessions = []
                current_user = session.uid

            # Extracts a list of tuples (type_id, count(type_id))
            histogram = Action.query.join(Action, Session.actions)\
                    .filter(Session.id == session.id)\
                    .with_entities(Action.type_id,
                                   func.count(Action.type_id))\
                    .group_by(Action.type_id)\
                    .order_by(Action.type_id)

            # Python IDs start at 1; C++ expects starting at 0, so shift
            # all IDs down by one
            mod_hist = [(type_id - 1, count) for (type_id, count) in histogram]
            user_sessions.append(mdmm_sampler.Session(mod_hist))

        if user_sessions:
            training_data.append(user_sessions)

        options = mdmm_sampler.MDMM.Options(
            num_topics=self.role_count,
            num_actions=len(ActionType),
            alpha=self.proportion_smoothing,
            beta=self.role_smoothing)
        rng = mdmm_sampler.random.Xoroshiro128(47)
        sampler = mdmm_sampler.MDMM(training_data, options, rng)
        sampler.run(training_data, self.max_iterations, rng, progress_report)

        # Create the roles
        roles = []
        for role_num in range(0, self.role_count):
            role = Role(analysis=self)
            roles.append(role)
            db.session.add(role)
            for action_type in ActionType:
                prob = sampler.action_probability(role_num,
                                                  int(action_type) - 1)
                weight = ActionWeight(
                    role=role, type_id=int(action_type), weight=prob)
                db.session.add(weight)

        def create_role_proportions(user_number, uid):
            for role_id, role in enumerate(roles):
                prob = sampler.role_probability(user_number, role_id)
                proportion = RoleProportion(
                    uid=uid, analysis=self, role=role, weight=prob)
                db.session.add(proportion)

        # Create the session role assignments and user role proportions
        user_id = -1
        current_user = None
        for idx, sess in enumerate(sessions):
            if current_user != session.uid:
                user_id += 1
                current_user = session.uid
                create_role_proportions(user_id, current_user)

            session = Session.query.get(sess.id)
            session.role = roles[sampler.topic_assignment(idx)]
        db.session.commit()


session_action = db.Table(
    'session_action',
    db.Column(
        'session_id',
        db.Integer,
        db.ForeignKey('session.id'),
        primary_key=True),
    db.Column(
        'action_id', db.Integer, db.ForeignKey('action.id'), primary_key=True))


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(120), nullable=False, index=True)
    analysis_id = db.Column(
        db.Integer, db.ForeignKey('analysis.id'), nullable=False)
    analysis = db.relationship(
        'Analysis',
        backref=db.backref(
            'sessions', lazy=True, cascade='all, delete-orphan'))
    role_id = db.Column(
        db.Integer, db.ForeignKey('role.id'), nullable=True, default=None)
    role = db.relationship('Role')
    actions = db.relationship('Action', secondary=session_action, lazy=False)


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(
        db.Integer, db.ForeignKey('analysis.id'), nullable=False)
    analysis = db.relationship(
        'Analysis',
        backref=db.backref('roles', lazy=True, cascade='all, delete-orphan'))


class ActionWeight(db.Model):
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)
    role = db.relationship(
        'Role',
        backref=db.backref(
            'weights', lazy=False, cascade='all, delete-orphan'))
    type_id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=True)


class RoleProportion(db.Model):
    uid = db.Column(db.String(120), primary_key=True)
    analysis_id = db.Column(
        db.Integer, db.ForeignKey('analysis.id'), primary_key=True)
    analysis = db.relationship(
        'Analysis',
        backref=db.backref(
            'proportions', lazy=False, cascade='all, delete-orphan'))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)
    role = db.relationship('Role')
    weight = db.Column(db.Float, nullable=False)
