# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from osv import fields, osv
from mx import DateTime as dt

class hr_evaluation_plan(osv.osv):
    _name = "hr_evaluation.plan"
    _description = "Evaluation Plan"
    _columns = {
        'name': fields.char("Evaluation Plan", size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'phase_ids' : fields.one2many('hr_evaluation.plan.phase', 'plan_id', 'Evaluation Phases'),
        'month_first': fields.integer('First Evaluation After'),
        'month_next': fields.integer('Next Evaluation After'),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active' : lambda *a: True,
    }
hr_evaluation_plan()

class hr_evaluation_plan_phase(osv.osv):
    _name = "hr_evaluation.plan.phase"
    _description = "Evaluation Plan Phase"
    _order = "sequence"
    _columns = {
        'name': fields.char("Phase", size=64, required=True),
        'sequence': fields.integer("Sequence"),
        'company_id': fields.related('plan_id','company_id',type='many2one',relation='res.company',string='Company',store=True),
        'plan_id': fields.many2one('hr_evaluation.plan','Evaluation Plan', required=True, ondelete='cascade'),
        'action': fields.selection([
            ('top-down','Top-Down Appraisal Requests'),
            ('bottom-up','Bottom-Up Appraisal Requests'),
            ('self','Self Appraisal Requests'),
            ('final','Final Interview')], 'Action', required=True),
        'survey_id': fields.many2one('survey','Appraisal Form',required=True),
        'send_answer_manager': fields.boolean('All Answers',
            help="Send all answers to the manager"),
        'send_answer_employee': fields.boolean('All Answers',
            help="Send all answers to the employee"),
        'send_anonymous_manager': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the manager"),
        'send_anonymous_employee': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the employee"),
        'wait': fields.boolean('Wait Previous Phases',
            help="Check this box if you want to wait that all preceeding phases " +
              "are finished before launching this phase.")

    }
    _defaults = {
        'sequence' : lambda *a: 1,
    }
hr_evaluation_plan_phase()

class hr_employee(osv.osv):
    _inherit="hr.employee"
    _columns = {
        'evaluation_plan_id': fields.many2one('hr_evaluation.plan', 'Evaluation Plan'),
        'evaluation_date': fields.date('Next Evaluation', help="Date of the next evaluation",readonly=True),
    }
    
    def onchange_evaluation_plan_id(self,cr,uid,ids,evaluation_plan_id,context={}):
        evaluation_date = self.browse(cr, uid, ids)[0].evaluation_date or ''
        evaluation_plan_obj=self.pool.get('hr_evaluation.plan')
        if evaluation_plan_id:
            for evaluation_plan in evaluation_plan_obj.browse(cr,uid,[evaluation_plan_id]):
                if not evaluation_date:
                   evaluation_date=(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d'))+ dt.RelativeDateTime(months=+evaluation_plan.month_first)).strftime('%Y-%m-%d')
                else:
                   evaluation_date=(dt.ISO.ParseAny(evaluation_date)+ dt.RelativeDateTime(months=+evaluation_plan.month_next)).strftime('%Y-%m-%d')
        return {'value': {'evaluation_date':evaluation_date}}
hr_employee()

class hr_evaluation_interview(osv.osv):
    _name = "hr.evaluation.interview"
    _inherit = "survey.request"
    
    def default_get(self, cr, uid, fields, context={}):
        data = super(hr_evaluation_interview, self).default_get(cr, uid, fields, context)
        if context.has_key('phase_id'):
            data['survey_id'] =self.pool.get('hr_evaluation.plan.phase').browse(cr, uid, context['phase_id']).survey_id.id
        return data

    _columns = {
        'user_to_review_id': fields.many2one('hr.employee', 'Employee'),
    }
hr_evaluation_interview()

class hr_evaluation(osv.osv):
    _name = "hr_evaluation.evaluation"
    _description = "Employee Evaluation"
    _rec_name = 'employee_id'
    _columns = {
        'date': fields.date("Evaluation Deadline", required=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'note_summary': fields.text('Evaluation Summary'),
        'note_action': fields.text('Action Plan',
            help="If the evaluation does not meet the expectations, you can propose"+
              "an action plan"),
        'rating': fields.selection([
            ('0','Significantly bellow expectations'),
            ('1','Did not meet expectations'),
            ('2','Meet expectations'),
            ('3','Exceeds expectations'),
            ('4','Significantly exceeds expectations'),
        ], "Overall Rating", help="This is the overall rating on that summarize the evaluation"),
        'survey_request_ids': fields.many2many('hr.evaluation.interview',
            'hr_evaluation_evaluation_requests',
            'evaluation_id',
            'survey_id',
            'Appraisal Forms'),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', required=True),
        'phase_id': fields.many2one('hr_evaluation.plan.phase', 'Phase'),
        'state': fields.selection([
            ('draft','Draft'),
            ('wait','Plan In Progress'),
            ('progress','Final Validation'),
            ('done','Done'),
            ('cancel','Cancelled'),
        ], 'State', required=True,readonly=True),
        'date_close': fields.date('Ending Date')
    }
    _defaults = {
        'date' : lambda *a: time.strftime('%Y-%m-%d'),
        'state' : lambda *a: 'draft',
    }

    def button_plan_in_progress(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'wait'})
        return True

    def button_final_validation(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'progress'})
        return True

    def button_done(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'done', 'date_close': time.strftime('%Y-%m-%d')})
        return True

    def button_cancel(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'cancel'})
        return True

hr_evaluation()

