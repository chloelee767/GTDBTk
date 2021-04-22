import logging
import os
from collections import defaultdict

from gtdbtk.biolib_lite.common import canonical_gid
from gtdbtk.biolib_lite.execute import check_dependencies
from gtdbtk.biolib_lite.taxonomy import Taxonomy
from gtdbtk.config.config import (FASTANI_DIR,
                                  FASTANI_GENOMES_EXT,
                                  FASTANI_GENOME_LIST,
                                  TAXONOMY_FILE,
                                  AF_THRESHOLD)
from gtdbtk.config.output import DIR_ANI_REP_INT_MASH
from gtdbtk.external.fastani import FastANI
from gtdbtk.external.mash import Mash
from gtdbtk.io.gtdb_radii import GTDBRadiiFile


class ANIRep(object):
    """Computes a list of genomes to a list of representatives."""

    def __init__(self, cpus):
        """Instantiate the ANI rep class.

        Parameters
        ----------
        cpus : int
            The maximum number of CPUs available to this workflow.
        """
        self.logger = logging.getLogger('timestamp')
        self.cpus = cpus

    @staticmethod
    def check_dependencies(no_mash):
        """Exits the system if the required programs are not on the path.

        Parameters
        ----------
        no_mash : bool
            True if Mash will be used, False otherwise.
        """
        dependencies = ['fastANI']
        if not no_mash:
            dependencies.append('mash')
        check_dependencies(dependencies)

    @staticmethod
    def _get_ref_genomes():
        """Returns a dictionary of genome accession to genome path.

        Returns
        -------
        dict[str, str]
            Dict[genome_id] = fasta_path
        """
        ref_genomes = dict()
        with open(FASTANI_GENOME_LIST) as g_path_file:
            for line in g_path_file:
                (full_name, path) = line.strip().split()
                if full_name.endswith(FASTANI_GENOMES_EXT):
                    accession = full_name.split(FASTANI_GENOMES_EXT)[0]
                ref_genomes[accession] = os.path.join(FASTANI_DIR, path, full_name)
        return ref_genomes

    def run(self, genomes, no_mash, max_d, out_dir, prefix, mash_k, mash_v, mash_s, min_af, mash_db):
        """Runs the pipeline.

        Parameters
        ----------
        genomes : dict[str, str]
            Dict[genome_id] = fasta_path
        no_mash : bool
            True if Mash should be used for pre-filtering, False otherwise.
        max_d : float
             maximum distance to keep [0-1]
        out_dir : str
            The directory to write the output files to.
        prefix : str
            The prefix to use when writing output files.
        mash_k : int
            k-mer size [1-32]
        mash_v : float
            maximum p-value to keep [0-1]
        mash_s : int
            maximum number of non-redundant hashes
        min_af : float
            alignment fraction to consider closest genome
        mash_db : Optional[str]
            The path to read/write the pre-computed Mash reference sketch database.
        """
        self.check_dependencies(no_mash)

        self.logger.info('Loading reference genomes.')
        ref_genomes = self._get_ref_genomes()
        d_compare = defaultdict(set)
        d_paths = {**genomes, **ref_genomes}

        # Pre-filter using Mash if specified.
        if not no_mash:
            dir_mash = os.path.join(out_dir, DIR_ANI_REP_INT_MASH)

            mash = Mash(self.cpus, dir_mash, prefix)
            self.logger.info(f'Using Mash version {mash.version()}')
            mash_results = mash.run(genomes, ref_genomes, max_d, mash_k, mash_v, mash_s, mash_db)
            for qry_gid, ref_hits in mash_results.items():
                d_compare[qry_gid] = d_compare[qry_gid].union(set(ref_hits.keys()))

        # Compare against all reference genomes.
        else:
            for qry_gid in genomes:
                d_compare[qry_gid] = set(ref_genomes.keys())

        self.logger.info(f'Calculating ANI with FastANI v{FastANI._get_version()}.')
        fastani = FastANI(self.cpus, force_single=True)
        fastani_results = fastani.run(d_compare, d_paths)

        taxonomy = Taxonomy().read(TAXONOMY_FILE, canonical_ids=True)
        ANISummaryFile(out_dir, prefix, fastani_results, taxonomy)
        ANIClosestFile(out_dir,
                       prefix,
                       fastani_results,
                       genomes,
                       min_af,
                       taxonomy)


class ANISummaryFile(object):
    name = 'ani_summary.tsv'

    def __init__(self, root, prefix, results, taxonomy):
        """Writes the ANI summary file generated by this pipeline.

        Parameters
        ----------
        root : str
            The directory to write the summary file to.
        prefix : str
            The output file prefix.
        results: dict[str, dict[str, dict[str, float]]]
            FastANI results.
        taxonomy : dict[str, tuple[str, str, str, str, str, str, str]]
            d[unique_id] -> [d__<taxon>, ..., s__<taxon>]
        """
        self.path = os.path.join(root, f'{prefix}.{self.name}')
        self.results = results
        self.taxonomy = taxonomy
        self.logger = logging.getLogger('timestamp')
        self._write()

    def _write(self):
        with open(self.path, 'w') as fh:
            fh.write('user_genome\treference_genome\tfastani_ani\tfastani_af\treference_taxonomy\n')
            for qry_gid, ref_hits in sorted(self.results.items()):
                for ref_gid, ref_hit in sorted(ref_hits.items(), key=lambda x: (-x[1]['af'], -x[1]['ani'], x[0])):
                    canonical_rid = canonical_gid(ref_gid)
                    taxonomy_str = ';'.join(self.taxonomy[canonical_rid])
                    fh.write(f'{qry_gid}\t{ref_gid}')
                    fh.write(f'\t{ref_hit["ani"]}\t{ref_hit["af"]}')
                    fh.write(f'\t{taxonomy_str}\n')
        self.logger.info(f'Summary of results saved to: {self.path}')


class ANIClosestFile(object):
    name = 'ani_closest.tsv'

    def __init__(self, root, prefix, results, genomes, min_af, taxonomy):
        """Writes the ANI closest file generated by this pipeline.

        Parameters
        ----------
        root : str
            The directory to write the summary file to.
        prefix : str
            The output file prefix.
        results: dict[str, dict[str, dict[str, float]]]
            FastANI results.
        genomes : dict[str, str]
            Dict[genome_id] = fasta_path
        min_af : float
            alignment fraction to consider closest genome
        taxonomy: dict[str, tuple[str, str, str, str, str, str, str]]
            d[unique_id] -> [d__<taxon>, ..., s__<taxon>]
        """
        self.logger = logging.getLogger('timestamp')
        self.path = os.path.join(root, f'{prefix}.{self.name}')
        self.results = results
        self.genomes = genomes
        self.min_af = min_af
        self.taxonomy = taxonomy
        self.gtdb_radii = GTDBRadiiFile()
        self._write()

    def _write(self):
        with open(self.path, 'w') as fh:
            fh.write('user_genome\treference_genome\tfastani_ani\tfastani_af\t'
                     'reference_taxonomy\tsatisfies_gtdb_circumscription_criteria\n')
            for gid in sorted(self.genomes):
                if gid in self.results:
                    thresh_results = [(ref_gid, hit) for (ref_gid, hit) in
                                      self.results[gid].items() if hit['af'] >= self.min_af]
                    closest = sorted(thresh_results, key=lambda x: (-x[1]['ani'], -x[1]['af']))
                    if len(closest) > 0:
                        ref_gid = closest[0][0]
                        canonical_rid = canonical_gid(ref_gid)
                        taxonomy_str = ';'.join(self.taxonomy[canonical_rid])
                        gtdb_ani_radius = self.gtdb_radii.get_rep_ani(canonical_rid)
                        closest_ani = closest[0][1]["ani"]
                        closest_af = closest[0][1]["af"]

                        fh.write(f'{gid}\t{ref_gid}')
                        fh.write(f'\t{closest_ani}\t{closest_af}')
                        fh.write(f'\t{taxonomy_str}')
                        fh.write(f'\t{closest_ani >= gtdb_ani_radius and closest_af >= AF_THRESHOLD}\n')
                    else:
                        fh.write(f'{gid}\tno result\tno result\tno result\tno result\tno result\n')
                else:
                    fh.write(f'{gid}\tno result\tno result\tno result\tno result\n')
        self.logger.info(f'Closest representative hits saved to: {self.path}')
