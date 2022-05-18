from .base import *


class Joiner2(Primitive):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def out_crd(self):
        pass

    @abstractmethod
    def out_ref1(self):
        pass

    @abstractmethod
    def out_ref2(self):
        pass


class Intersect2(Joiner2):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.in_ref1 = []
        self.in_ref2 = []
        self.in_crd1 = []
        self.in_crd2 = []

        self.size_in_ref1 = 0
        self.size_in_ref2 = 0
        self.size_in_crd1 = 0
        self.size_in_crd2 = 0

        self.ocrd = 0
        self.oref1 = 0
        self.oref2 = 0

        self.curr_crd1 = None
        self.curr_crd2 = None
        self.curr_ref1 = None
        self.curr_ref2 = None

        self.total_count =0;
        self.count =0;
    def update(self):
        if len(self.in_crd1) > 0 and len(self.in_crd2) > 0:
            # FIXME: See when only one 'D' signal is present
            if self.curr_crd1 == 'D' or self.curr_crd2 == 'D':
                self.done = True
                self.ocrd = 'D'
                self.oref1 = 'D'
                self.oref2 = 'D'
            elif self.curr_crd2 == self.curr_crd1:
                self.ocrd = '' if self.curr_crd2 is None else self.curr_crd1
                self.oref1 = '' if self.curr_ref1 is None else self.curr_ref1
                self.oref2 = '' if self.curr_ref2 is None else self.curr_ref2
                self.curr_crd1 = self.in_crd1.pop(0)
                self.curr_crd2 = self.in_crd2.pop(0)
                self.curr_ref1 = self.in_ref1.pop(0)
                self.curr_ref2 = self.in_ref2.pop(0)
                self.total_count +=1
                self.count +=1 
            elif is_stkn(self.curr_crd1):
                self.ocrd = ''
                self.oref1 = ''
                self.oref2 = ''
                self.curr_crd2 = self.in_crd2.pop(0)
                self.curr_ref2 = self.in_ref2.pop(0)
                self.total_count +=1
            elif is_stkn(self.curr_crd2):
                self.ocrd = ''
                self.oref1 = ''
                self.oref2 = ''
                self.curr_crd1 = self.in_crd1.pop(0)
                self.curr_ref1 = self.in_ref1.pop(0)
                self.total_count +=1
            elif self.curr_crd1 < self.curr_crd2:
                self.ocrd = ''
                self.oref1 = ''
                self.oref2 = ''
                self.curr_crd1 = self.in_crd1.pop(0)
                self.curr_ref1 = self.in_ref1.pop(0)
                self.total_count +=1
            elif self.curr_crd1 > self.curr_crd2:
                self.ocrd = ''
                self.oref1 = ''
                self.oref2 = ''
                self.curr_crd2 = self.in_crd2.pop(0)
                self.curr_ref2 = self.in_ref2.pop(0)
                self.total_count +=1
            else:
                raise Exception('Intersect2: should not enter this case')
        else:
            # Do Nothing if no inputs are detected
            if self.curr_crd1 == 'D' or self.curr_crd2 == 'D':
                self.done = True
                self.ocrd = 'D'
                self.oref1 = 'D'
                self.oref2 = 'D'
                self.curr_crd1 = ''
                self.curr_crd2 = ''
                self.curr_ref1 = ''
                self.curr_ref2 = ''
            else:
                self.ocrd = ''
                self.oref1 = ''
                self.oref2 = ''
        self.compute_fifos()


        if self.debug:
            print("DEBUG: INTERSECT: \t OutCrd:", self.ocrd, "\t Out Ref1:", self.oref1, "\t Out Ref2:", self.oref2,
                  "\t Crd1:", self.curr_crd1, "\t Ref1:", self.curr_ref1,
                  "\t Crd2:", self.curr_crd2, "\t Ref2", self.curr_ref2, "\t Intersection rate: ", self.count/self.total_count) 

    def set_in1(self, in_ref1, in_crd1):
        if in_ref1 != '' and in_crd1 != '':
            self.in_ref1.append(in_ref1)
            self.in_crd1.append(in_crd1)

    def set_in2(self, in_ref2, in_crd2):
        if in_ref2 != '' and in_crd2 != '':
            self.in_ref2.append(in_ref2)
            self.in_crd2.append(in_crd2)

    def compute_fifos(self):
        self.size_in_ref1 = max(self.size_in_ref1, len(self.in_ref1))
        self.size_in_ref2 = max(self.size_in_ref2, len(self.in_ref2)) 
        self.size_in_crd1 = max(self.size_in_crd1, len(self.in_crd1))
        self.size_in_crd2 = max(self.size_in_crd2, len(self.in_crd2))

    def print_fifos(self):
        print("FIFO in ref 1: ", self.size_in_ref1)
        print("FIFO in ref 2: ", self.size_in_ref2)
        print("FIFO in crd 1: ", self.size_in_crd1)
        print("FIFO in crd 2: ", self.size_in_crd2)

    def out_crd(self):
        return self.ocrd

    def out_ref1(self):
        return self.oref1

    def out_ref2(self):
        return self.oref2

    def return_intersection_rate(self):
        return self.count/self.total_count

