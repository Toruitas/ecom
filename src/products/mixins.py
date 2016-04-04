from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404

class StaffRequiredMixin(object):
    """
    takes an object
    Reroutes user who isn't logged in to normal login, but tests the staff required status on disptch. If we want to hide
    admin, or if admin isn't activated.
    """
    @classmethod
    def as_view(self, *args,**kwargs):
        view = super(StaffRequiredMixin,self).as_view(*args,**kwargs)
        return login_required(view)  # return staff_member_required(view)

    @method_decorator(login_required)
    def dispatch(self,request,*args,**kwargs):
        """
        if we wanted to change this to based off of different model we could, instead of user
        :param request:
        :param arg:
        :param kwargs:
        :return:
        """
        if request.user.is_staff:
            return super(StaffRequiredMixin, self).dispatch(request, *args,**kwargs)
        else:
            raise Http404


class LoginRequiredMixin(object):
    """
    reroutes user to normal login
    """
    @classmethod
    def as_view(self, *args,**kwargs):
        view = super(LoginRequiredMixin,self).as_view(*args,**kwargs)
        return login_required(view)

    @method_decorator(login_required)
    def dispatch(self,request,*arg,**kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args,**kwargs)